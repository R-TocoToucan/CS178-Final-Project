import duckdb
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB = "headways.duckdb"

def query(sql, params=None):
    con = duckdb.connect(DB, read_only=True)
    result = con.execute(sql, params or []).df()
    con.close()
    return result


@app.route("/")
def index():
    return render_template("index.html")

# 1. Headway distribution by branch
@app.route("/api/distribution")
def distribution():
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    day_type = request.args.get("day_type", "all")

    where = ["headway_branch_seconds IS NOT NULL"]
    if exclude_terminal:
        where.append("is_terminal = false")
    if day_type != "all":
        where.append(f"day_type = '{day_type}'")

    sql = f"""
        SELECT
            branch_route_id,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS q1,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS q3,
            AVG(headway_branch_seconds) / 60.0 AS mean,
            COUNT(*) FILTER (WHERE headway_branch_seconds > 1080) * 100.0 / COUNT(*) AS long_gap_pct,
            COUNT(*) FILTER (WHERE headway_branch_seconds IS NULL) * 100.0 / COUNT(*) AS null_pct
        FROM headways_enriched
        WHERE {" AND ".join(where)}
          AND branch_route_id IS NOT NULL
        GROUP BY branch_route_id
        ORDER BY branch_route_id
    """
    return jsonify(query(sql).to_dict(orient="records"))

# 2. GLX vs Green-E comparison
@app.route("/api/glx_comparison")
def glx_comparison():
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    day_type = request.args.get("day_type", "all")

    where = ["headway_branch_seconds IS NOT NULL",
             "branch_route_id = 'Green-E'"]
    if exclude_terminal:
        where.append("is_terminal = false")
    if day_type != "all":
        where.append(f"day_type = '{day_type}'")

    sql = f"""
        SELECT
            CASE
                WHEN parent_station IN (
                    'place-lech','place-spmnl','place-gilmn',
                    'place-esomr','place-mgngl','place-balsq','place-mdftf'
                ) THEN 'GLX'
                ELSE 'Green-E (non-GLX)'
            END AS group,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS q1,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS q3,
            AVG(headway_branch_seconds) / 60.0 AS mean,
            STDDEV(headway_branch_seconds) / 60.0 AS stddev,
            COUNT(*) FILTER (WHERE headway_branch_seconds > 1080) * 100.0 / COUNT(*) AS long_gap_pct,
            COUNT(*) AS n
        FROM headways_enriched
        WHERE {" AND ".join(where)}
        GROUP BY 1
    """
    return jsonify(query(sql).to_dict(orient="records"))

# 3. Hour-of-day breakdown
@app.route("/api/by_hour")
def by_hour():
    branch = request.args.get("branch", "Green-E")
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    day_type = request.args.get("day_type", "all")

    where = ["headway_branch_seconds IS NOT NULL",
             "hour_of_day IS NOT NULL",
             f"branch_route_id = '{branch}'"]
    if exclude_terminal:
        where.append("is_terminal = false")
    if day_type != "all":
        where.append(f"day_type = '{day_type}'")

    sql = f"""
        SELECT
            hour_of_day,
            AVG(headway_branch_seconds) / 60.0 AS mean_headway,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS median_headway,
            COUNT(*) FILTER (WHERE headway_branch_seconds > 1080) * 100.0 / COUNT(*) AS long_gap_pct
        FROM headways_enriched
        WHERE {" AND ".join(where)}
        GROUP BY hour_of_day
        ORDER BY hour_of_day
    """
    return jsonify(query(sql).to_dict(orient="records"))

# 4. Missingness by stop
@app.route("/api/missingness")
def missingness():
    branch = request.args.get("branch", "Green-E")

    sql = f"""
        SELECT
            stop_name,
            parent_station,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE headway_branch_seconds IS NULL) * 100.0 / COUNT(*) AS null_pct,
            is_terminal
        FROM headways_enriched
        WHERE branch_route_id = '{branch}'
        GROUP BY stop_name, parent_station, is_terminal
        HAVING COUNT(*) >= 1000
        ORDER BY null_pct DESC
    """
    return jsonify(query(sql).to_dict(orient="records"))

# 5. Direction toggle
@app.route("/api/by_direction")
def by_direction():
    branch = request.args.get("branch", "Green-E")
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    day_type = request.args.get("day_type", "all")

    where = ["headway_branch_seconds IS NOT NULL",
             f"branch_route_id = '{branch}'"]
    if exclude_terminal:
        where.append("is_terminal = false")
    if day_type != "all":
        where.append(f"day_type = '{day_type}'")

    sql = f"""
        SELECT
            direction,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS q1,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS q3,
            AVG(headway_branch_seconds) / 60.0 AS mean,
            STDDEV(headway_branch_seconds) / 60.0 AS stddev,
            COUNT(*) FILTER (WHERE headway_branch_seconds > 1080) * 100.0 / COUNT(*) AS long_gap_pct
        FROM headways_enriched
        WHERE {" AND ".join(where)}
        GROUP BY direction
    """
    return jsonify(query(sql).to_dict(orient="records"))

# 6. Long-gap event browser
@app.route("/api/long_gaps")
def long_gaps():
    branch = request.args.get("branch", "Green-E")
    limit = int(request.args.get("limit", 100))
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"

    where = [f"branch_route_id = '{branch}'",
             "headway_branch_seconds > 1080"]
    if exclude_terminal:
        where.append("is_terminal = false")

    sql = f"""
        SELECT
            service_date,
            stop_name,
            parent_station,
            direction,
            day_type,
            hour_of_day,
            headway_branch_seconds / 60.0 AS headway_minutes
        FROM headways_enriched
        WHERE {" AND ".join(where)}
        ORDER BY headway_branch_seconds DESC
        LIMIT {limit}
    """
    return jsonify(query(sql).to_dict(orient="records"))

# 7. Month-by-month trend
@app.route("/api/by_month")
def by_month():
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    day_type = request.args.get("day_type", "all")

    where = ["headway_branch_seconds IS NOT NULL"]
    if exclude_terminal:
        where.append("is_terminal = false")
    if day_type != "all":
        where.append(f"day_type = '{day_type}'")

    sql = f"""
        SELECT
            month,
            CASE
                WHEN parent_station IN (
                    'place-lech','place-spmnl','place-gilmn',
                    'place-esomr','place-mgngl','place-balsq','place-mdftf'
                ) THEN 'GLX'
                ELSE 'Green-E (non-GLX)'
            END AS group,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS median,
            AVG(headway_branch_seconds) / 60.0 AS mean,
            STDDEV(headway_branch_seconds) / 60.0 AS stddev,
            COUNT(*) FILTER (WHERE headway_branch_seconds > 1080) * 100.0 / COUNT(*) AS long_gap_pct
        FROM headways_enriched
        WHERE {" AND ".join(where)}
          AND branch_route_id = 'Green-E'
        GROUP BY month, 2
        ORDER BY month, 2
    """
    return jsonify(query(sql).to_dict(orient="records"))

# 8. Effective headway cross-line
@app.route("/api/cross_line")
def cross_line():
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    day_type = request.args.get("day_type", "all")

    where = ["headway_trunk_seconds IS NOT NULL"]
    if exclude_terminal:
        where.append("is_terminal = false")
    if day_type != "all":
        where.append(f"day_type = '{day_type}'")

    sql = f"""
        SELECT
            trunk_route_id,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY headway_trunk_seconds) / 60.0 AS median,
            AVG(headway_trunk_seconds) / 60.0 AS mean,
            STDDEV(headway_trunk_seconds) / 60.0 AS stddev,
            COUNT(*) FILTER (WHERE headway_trunk_seconds > 1080) * 100.0 / COUNT(*) AS long_gap_pct,
            COUNT(*) AS n
        FROM headways_enriched
        WHERE {" AND ".join(where)}
        GROUP BY trunk_route_id
        ORDER BY trunk_route_id
    """
    return jsonify(query(sql).to_dict(orient="records"))

if __name__ == "__main__":
    app.run(port=5001, debug=True)