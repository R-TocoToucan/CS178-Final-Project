import duckdb
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB = "headways.duckdb"

GLX_STATIONS = (
    "'place-lech','place-spmnl','place-gilmn',"
    "'place-esomr','place-mgngl','place-balsq','place-mdftf'"
)

GROUP_CASE = f"""
    CASE
        WHEN parent_station IN ({GLX_STATIONS})
            THEN 'GLX'
        WHEN branch_route_id = 'Green-E'
            THEN 'Green-E (non-GLX)'
        WHEN branch_route_id IN ('Green-B','Green-C','Green-D')
            THEN 'Green (other branches)'
        WHEN trunk_route_id = 'Red'
            THEN 'Red Line'
        WHEN trunk_route_id = 'Orange'
            THEN 'Orange Line'
        WHEN trunk_route_id = 'Blue'
            THEN 'Blue Line'
        WHEN trunk_route_id = 'Mattapan'
            THEN 'Mattapan'
        ELSE NULL
    END
"""

HEADWAY_CASE = f"""
    CASE
        WHEN parent_station IN ({GLX_STATIONS})
            THEN headway_branch_seconds
        WHEN branch_route_id IN ('Green-B','Green-C','Green-D','Green-E')
            THEN headway_branch_seconds
        ELSE headway_trunk_seconds
    END
"""

def query(sql, params=None):
    con = duckdb.connect(DB, read_only=True)
    result = con.execute(sql, params or []).df()
    con.close()
    return result


@app.route("/")
def index():
    return render_template("index.html")


# 1. Network-wide comparison — GLX vs all reference groups
@app.route("/api/network_comparison")
def network_comparison():
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    day_type = request.args.get("day_type", "all")
    direction = request.args.get("direction", "all")

    where = [f"({HEADWAY_CASE}) IS NOT NULL",
             f"({GROUP_CASE}) IS NOT NULL"]
    if exclude_terminal:
        where.append("is_terminal = false")
    if day_type != "all":
        where.append(f"day_type = '{day_type}'")
    if direction != "all":
        where.append(f"direction_normalized = '{direction}'")

    sql = f"""
        SELECT
            {GROUP_CASE} AS group,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {HEADWAY_CASE}) / 60.0 AS q1,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {HEADWAY_CASE}) / 60.0 AS median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {HEADWAY_CASE}) / 60.0 AS q3,
            AVG({HEADWAY_CASE}) / 60.0 AS mean,
            STDDEV({HEADWAY_CASE}) / 60.0 AS stddev,
            COUNT(*) FILTER (WHERE {HEADWAY_CASE} > 1080) * 100.0 / COUNT(*) AS long_gap_pct,
            COUNT(*) AS n
        FROM headways_enriched
        WHERE {" AND ".join(where)}
        GROUP BY 1
        ORDER BY
            CASE {GROUP_CASE}
                WHEN 'GLX' THEN 1
                WHEN 'Green-E (non-GLX)' THEN 2
                WHEN 'Green (other branches)' THEN 3
                WHEN 'Red Line' THEN 4
                WHEN 'Orange Line' THEN 5
                WHEN 'Blue Line' THEN 6
                WHEN 'Mattapan' THEN 7
            END
    """
    return jsonify(query(sql).to_dict(orient="records"))


# 2. Hour-of-day: GLX vs Green-E non-GLX
@app.route("/api/by_hour")
def by_hour():
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    day_type = request.args.get("day_type", "all")
    direction = request.args.get("direction", "all")

    where = ["headway_branch_seconds IS NOT NULL",
             "hour_of_day IS NOT NULL",
             "branch_route_id = 'Green-E'"]
    if exclude_terminal:
        where.append("is_terminal = false")
    if day_type != "all":
        where.append(f"day_type = '{day_type}'")
    if direction != "all":
        where.append(f"direction_normalized = '{direction}'")

    sql = f"""
        SELECT
            hour_of_day,
            CASE
                WHEN parent_station IN ({GLX_STATIONS}) THEN 'GLX'
                ELSE 'Green-E (non-GLX)'
            END AS group,
            AVG(headway_branch_seconds) / 60.0 AS mean_headway,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS median_headway,
            COUNT(*) FILTER (WHERE headway_branch_seconds > 1080) * 100.0 / COUNT(*) AS long_gap_pct
        FROM headways_enriched
        WHERE {" AND ".join(where)}
        GROUP BY hour_of_day, 2
        ORDER BY hour_of_day, 2
    """
    return jsonify(query(sql).to_dict(orient="records"))


# 3. Day type: GLX vs Green-E non-GLX
@app.route("/api/by_daytype")
def by_daytype():
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    direction = request.args.get("direction", "all")

    where = ["headway_branch_seconds IS NOT NULL",
             "branch_route_id = 'Green-E'"]
    if exclude_terminal:
        where.append("is_terminal = false")
    if direction != "all":
        where.append(f"direction_normalized = '{direction}'")

    sql = f"""
        SELECT
            day_type,
            CASE
                WHEN parent_station IN ({GLX_STATIONS}) THEN 'GLX'
                ELSE 'Green-E (non-GLX)'
            END AS group,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY headway_branch_seconds) / 60.0 AS median,
            AVG(headway_branch_seconds) / 60.0 AS mean,
            STDDEV(headway_branch_seconds) / 60.0 AS stddev,
            COUNT(*) FILTER (WHERE headway_branch_seconds > 1080) * 100.0 / COUNT(*) AS long_gap_pct
        FROM headways_enriched
        WHERE {" AND ".join(where)}
        GROUP BY day_type, 2
        ORDER BY day_type, 2
    """
    return jsonify(query(sql).to_dict(orient="records"))


# 4. Missingness by stop (Green-E only)
@app.route("/api/missingness")
def missingness():
    direction = request.args.get("direction", "all")

    where = ["branch_route_id = 'Green-E'"]
    if direction != "all":
        where.append(f"direction_normalized = '{direction}'")

    sql = f"""
        SELECT
            stop_name,
            parent_station,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE headway_branch_seconds IS NULL) * 100.0 / COUNT(*) AS null_pct,
            is_terminal
        FROM headways_enriched
        WHERE {" AND ".join(where)}
        GROUP BY stop_name, parent_station, is_terminal
        HAVING COUNT(*) >= 500
        ORDER BY null_pct DESC
    """
    return jsonify(query(sql).to_dict(orient="records"))

# 5. Monthly trend — all line groups
@app.route("/api/by_month")
def by_month():
    exclude_terminal = request.args.get("exclude_terminal", "false") == "true"
    day_type = request.args.get("day_type", "all")
    direction = request.args.get("direction", "all")

    where = [f"({HEADWAY_CASE}) IS NOT NULL",
             f"({GROUP_CASE}) IS NOT NULL"]
    if exclude_terminal:
        where.append("is_terminal = false")
    if day_type != "all":
        where.append(f"day_type = '{day_type}'")
    if direction != "all":
        where.append(f"direction_normalized = '{direction}'")

    sql = f"""
        SELECT
            month,
            {GROUP_CASE} AS group,
            AVG({HEADWAY_CASE}) / 60.0 AS mean,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {HEADWAY_CASE}) / 60.0 AS median
        FROM headways_enriched
        WHERE {" AND ".join(where)}
        GROUP BY month, 2
        ORDER BY month, 2
    """
    return jsonify(query(sql).to_dict(orient="records"))

if __name__ == "__main__":
    app.run(port=5001, debug=True)