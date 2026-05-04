from __future__ import annotations

import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ITEM_ID = "84c9d171d32945f594fbb4d889153c44"
BASE = "https://www.arcgis.com/sharing/rest/content/items"
DATA_DIR = Path("data")
DOWNLOAD_DIR = Path("_mbta_download_temp")
CHUNK_SIZE = 1024 * 1024


def fetch_json(url: str) -> dict:
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8"))


def download_file(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urlopen(req, timeout=120) as response:
            total = int(response.headers.get("Content-Length") or 0)
            content_type = response.headers.get("Content-Type", "")
            print(f"Downloading: {url}")
            if total:
                print(f"Size: {total / (1024 ** 2):.1f} MB")
            print(f"Content-Type: {content_type}")

            written = 0
            start = time.time()
            with destination.open("wb") as f:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    written += len(chunk)
                    if total:
                        pct = written * 100 / total
                        mb = written / (1024 ** 2)
                        elapsed = max(time.time() - start, 0.001)
                        rate = mb / elapsed
                        print(f"\r  {pct:5.1f}%  {mb:,.1f} MB  {rate:,.1f} MB/s", end="")
            print()
    except HTTPError as e:
        raise RuntimeError(f"HTTP error {e.code} while downloading {url}: {e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Network error while downloading {url}: {e.reason}") from e

    return destination


def looks_like_html(path: Path) -> bool:
    sample = path.read_bytes()[:200].lower().strip()
    return sample.startswith(b"<!doctype") or sample.startswith(b"<html")


def extract_zip(zip_path: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            name = Path(member.filename).name
            if not name or member.is_dir():
                continue
            if name.lower().endswith(".csv"):
                target = output_dir / name
                with zf.open(member) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.append(target)
    return extracted


def maybe_extract_nested_zips(download_dir: Path, output_dir: Path) -> list[Path]:
    extracted: list[Path] = []
    for zip_path in download_dir.rglob("*.zip"):
        try:
            extracted.extend(extract_zip(zip_path, output_dir))
        except zipfile.BadZipFile:
            pass
    return extracted


def download_resources(output_dir: Path) -> list[Path]:
    resources_url = f"{BASE}/{ITEM_ID}/resources?f=json"
    resources = fetch_json(resources_url).get("resources", [])
    if not resources:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    for resource in resources:
        resource_name = resource.get("resource") or resource.get("name")
        if not resource_name:
            continue
        lower = resource_name.lower()
        if not (lower.endswith(".csv") or lower.endswith(".zip")):
            continue

        safe_name = Path(resource_name).name
        resource_url = f"{BASE}/{ITEM_ID}/resources/{quote(resource_name)}"
        dest = DOWNLOAD_DIR / safe_name
        downloaded.append(download_file(resource_url, dest))

    csvs: list[Path] = []
    for file in downloaded:
        if file.suffix.lower() == ".csv":
            target = output_dir / file.name
            shutil.move(str(file), str(target))
            csvs.append(target)
        elif file.suffix.lower() == ".zip":
            csvs.extend(extract_zip(file, output_dir))
    return csvs


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    metadata_url = f"{BASE}/{ITEM_ID}?f=json"
    metadata = fetch_json(metadata_url)
    if "error" in metadata:
        print(json.dumps(metadata["error"], indent=2))
        return 1

    print("Dataset:", metadata.get("title", "MBTA Rapid Transit Headways 2025"))
    print("Type:", metadata.get("type", "unknown"))
    if metadata.get("size"):
        print(f"Listed size: {metadata['size'] / (1024 ** 2):.1f} MB")

    # Main ArcGIS item-data download. For CSV Collection items this is usually a zip/file payload.
    item_data_url = f"{BASE}/{ITEM_ID}/data"
    payload = DOWNLOAD_DIR / "mbta_rapid_transit_headways_2025_item_data"
    downloaded = download_file(item_data_url, payload)

    csvs: list[Path] = []

    if zipfile.is_zipfile(downloaded):
        csvs.extend(extract_zip(downloaded, DATA_DIR))
    elif looks_like_html(downloaded):
        print("ArcGIS returned an HTML page instead of the file. Trying item resources...")
        csvs.extend(download_resources(DATA_DIR))
    else:
        # Sometimes the item-data endpoint returns a JSON manifest.
        try:
            manifest = json.loads(downloaded.read_text(encoding="utf-8"))
            print("Received JSON item data. Trying resources from the item...")
            print(json.dumps(manifest, indent=2)[:2000])
            csvs.extend(download_resources(DATA_DIR))
        except Exception:
            # It may be a single CSV file.
            csv_target = DATA_DIR / "mbta_rapid_transit_headways_2025.csv"
            shutil.move(str(downloaded), str(csv_target))
            csvs.append(csv_target)

    # Handle cases where resources included nested zip files.
    csvs.extend(maybe_extract_nested_zips(DOWNLOAD_DIR, DATA_DIR))

    # De-duplicate and report.
    csvs = sorted({p.resolve() for p in DATA_DIR.glob("*.csv")})
    print("\nDone.")
    print(f"CSV files in data/: {len(csvs)}")
    for p in csvs:
        print(f"  - {p.name} ({p.stat().st_size / (1024 ** 2):.1f} MB)")

    if len(csvs) == 0:
        print("\nNo CSVs were extracted. Open the MassGIS page manually and use Download > CSV Collection, then put the CSVs in data/.")
        return 2

    print("\nNext:")
    print("  py setup_db.py")
    print("  py app.py")
    print("  then open http://127.0.0.1:5001")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCanceled.")
        raise SystemExit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        raise SystemExit(1)
