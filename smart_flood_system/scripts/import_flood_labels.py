"""
Import verified positive flood-label days into the existing Smart Flood Monitoring System DB.
Unknown dates are deliberately NOT inserted as flood_occurred=0.
Run from project root with the project's virtual environment activated:
    python scripts/import_flood_labels.py
"""
import argparse
import csv
from datetime import date, datetime, time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from backend.database import SessionLocal
from backend.models import Location, FloodEvent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="data/flood_labels/historical_flood_labels_2020_2025.csv")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path.resolve()}")

    db = SessionLocal()
    inserted = 0
    skipped_unknown = 0
    skipped_location = 0
    try:
        locations = {row.location_id: row for row in db.scalars(select(Location)).all()}
        with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Blank means unknown/unverified, not a negative label.
                if row.get("label_status") != "confirmed_reported_flood" or row.get("flood_occurred") != "1":
                    skipped_unknown += 1
                    continue

                loc_id = int(row["location_id"])
                if loc_id not in locations:
                    print(f"Skipping {row['event_date']}: location_id {loc_id} not found in DB")
                    skipped_location += 1
                    continue

                event_day = date.fromisoformat(row["event_date"])
                source = (row.get("source_name") or "Historical flood label").strip()
                desc = (row.get("event_name") or "").strip()
                url = (row.get("source_url") or "").strip()
                confidence = (row.get("confidence") or "").strip()
                notes = (row.get("notes") or "").strip()
                description = f"{desc}. Confidence={confidence}. {notes} Source URL: {url}".strip()

                stmt = insert(FloodEvent).values(
                    location_id=loc_id,
                    event_date=event_day,
                    flood_occurred=True,
                    severity=None,
                    affected_area=None,
                    source=source[:120],
                    description=description[:1000]
                )
                stmt = stmt.on_duplicate_key_update(
                    flood_occurred=True,
                    description=description[:1000]
                )
                db.execute(stmt)
                inserted += 1

        db.commit()
        print(f"Finished. Positive label rows processed/upserted: {inserted}")
        print(f"Unknown dates intentionally skipped: {skipped_unknown}")
        print(f"Rows skipped because location_id was missing: {skipped_location}")
        print("No negative labels were created.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
