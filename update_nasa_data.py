
from datetime import date
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from backend.database import SessionLocal
from backend.models import Location
from backend.services.data_service import upsert_power_data


def main():
    parser = argparse.ArgumentParser(
        description="Download NASA POWER daily historical weather data."
    )
    parser.add_argument(
        "--start",
        default="2020-01-01",
        help="Start date in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--end",
        default="2025-09-30",
        help="End date in YYYY-MM-DD format."
    )
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    if end < start:
        parser.error("--end must not be earlier than --start")

    db = SessionLocal()

    try:
        locations = db.scalars(select(Location)).all()

        print(f"NASA POWER historical download: {start} to {end}")
        print(f"Locations found: {len(locations)}")

        for loc in locations:
            try:
                result = upsert_power_data(db, loc, start, end)
                print(f"[OK] {loc.location_name}: {result}")
            except Exception as e:
                db.rollback()
                print(f"[ERROR] {loc.location_name}: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    main()