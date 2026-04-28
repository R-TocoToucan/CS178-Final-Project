import duckdb
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB = "headways.duckdb"

def query(sql, params=None):
    con = duckdb.connect(DB, read_only=True)
    result = con.execute(sql, params or []).df()
    con.close()
    return result


# 1. Headway distribution by branch
@app.route("/api/distribution")
def distribution():
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    day_type = request.args.get("day_type", "all")  # all | weekday | weekend

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
        ORDER BY null_pct DESC
    """
    return jsonify(query(sql).to_dict(orient="records"))


if __name__ == "__main__":
    app.run(port=5001, debug=True)