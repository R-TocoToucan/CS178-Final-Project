import duckdb

con = duckdb.connect("headways.duckdb")

# Step 1: Load all 12 CSVs 
print("Loading CSVs...")
con.execute("""
    CREATE OR REPLACE TABLE headways AS
    SELECT
        TRY_CAST(service_date AS DATE)          AS service_date,
        route_id::VARCHAR                       AS route_id,
        trunk_route_id::VARCHAR                 AS trunk_route_id,
        branch_route_id::VARCHAR                AS branch_route_id,
        trip_id::VARCHAR                        AS trip_id,
        TRY_CAST(direction_id AS INTEGER)       AS direction_id,
        direction::VARCHAR                      AS direction,
        parent_station::VARCHAR                 AS parent_station,
        stop_id::VARCHAR                        AS stop_id,
        stop_name::VARCHAR                      AS stop_name,
        TRY_CAST(stop_departure_datetime AS TIMESTAMPTZ) AS stop_departure_datetime,
        TRY_CAST(stop_departure_sec AS BIGINT)  AS stop_departure_sec,
        TRY_CAST(headway_trunk_seconds AS BIGINT) AS headway_trunk_seconds,
        TRY_CAST(headway_branch_seconds AS BIGINT) AS headway_branch_seconds
    FROM read_csv_auto('data/*.csv',
        all_varchar=true,
        union_by_name=true
    )
""")
print(f"Loaded: {con.execute('SELECT COUNT(*) FROM headways').fetchone()[0]:,} rows")

# Step 2: Flag terminal stops 
print("Flagging terminal stops...")
con.execute("""
    CREATE OR REPLACE TABLE terminal_stops AS
    SELECT DISTINCT parent_station
    FROM headways
    GROUP BY parent_station
    HAVING COUNT(*) FILTER (WHERE headway_branch_seconds IS NULL) * 1.0 / COUNT(*) > 0.9
""")

# Step 3: Build enriched table 
print("Building enriched table...")
con.execute("""
    CREATE OR REPLACE TABLE headways_enriched AS
    SELECT
        h.*,
        EXTRACT(DOW FROM h.service_date)        AS day_of_week,
        CASE
            WHEN EXTRACT(DOW FROM h.service_date) IN (0, 6) THEN 'weekend'
            ELSE 'weekday'
        END                                     AS day_type,
        EXTRACT(HOUR FROM h.stop_departure_datetime AT TIME ZONE 'America/New_York') AS hour_of_day,
        EXTRACT(MONTH FROM h.service_date)      AS month,
        CASE
            WHEN t.parent_station IS NOT NULL THEN true
            ELSE false
        END                                     AS is_terminal
    FROM headways h
    LEFT JOIN terminal_stops t ON h.parent_station = t.parent_station
""")

print("Done! Tables created: headways, terminal_stops, headways_enriched")
con.close()