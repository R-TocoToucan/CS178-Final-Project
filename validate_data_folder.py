#!/usr/bin/env python3
from pathlib import Path
import csv

DATA_DIR = Path("data")
EXPECTED_COLUMNS = {
    "service_date",
    "route_id",
    "trunk_route_id",
    "branch_route_id",
    "trip_id",
    "direction_id",
    "direction",
    "parent_station",
    "stop_id",
    "stop_name",
    "stop_departure_datetime",
    "stop_departure_sec",
    "headway_trunk_seconds",
    "headway_branch_seconds",
}

csvs = sorted(DATA_DIR.glob("*.csv"))
print(f"CSV files found: {len(csvs)}")
if not csvs:
    raise SystemExit("No CSV files found in ./data")

bad = False
for path in csvs:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = set(next(reader))
    missing = sorted(EXPECTED_COLUMNS - header)
    size_mb = path.stat().st_size / (1024 ** 2)
    if missing:
        bad = True
        print(f"[BAD] {path.name} ({size_mb:.1f} MB) missing columns: {missing}")
    else:
        print(f"[OK]  {path.name} ({size_mb:.1f} MB)")

if bad:
    raise SystemExit("Some CSVs are missing expected columns.")
print("Data folder looks usable for setup_db.py")
