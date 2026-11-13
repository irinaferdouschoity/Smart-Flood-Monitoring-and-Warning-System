"""Download all missing NASA POWER weather days into MySQL (no web server needed).

    python scripts/sync_nasa_data.py

First run on an empty database downloads 2020-01-01 -> yesterday for every
location. Later runs only fetch what is new. Safe to run repeatedly.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.data_service import sync_all_locations

if __name__ == "__main__":
    for r in sync_all_locations():
        if r["status"] == "success":
            print(f"[OK]    location {r['location_id']}: {r['records']} rows")
        else:
            print(f"[ERROR] location {r['location_id']}: {r['error']}")
