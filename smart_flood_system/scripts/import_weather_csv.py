"""Load the saved daily weather (2020-2026) into MySQL - no internet needed.

Reads data/city_specific_risk.csv, which already contains the NASA POWER
weather for all 6 cities. Run from the project root:
    python scripts/import_weather_csv.py

Safe to run more than once (existing days are updated, not duplicated).
"""
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert

from backend.database import SessionLocal
from backend.models import Location, WeatherObservation

CSV = Path(__file__).resolve().parents[1] / "data" / "city_specific_risk.csv"
FIELDS = [
    "precipitation", "temperature_avg", "temperature_max", "temperature_min",
    "humidity", "dew_point", "wind_speed", "surface_pressure",
]


def main():
    if not CSV.exists():
        raise SystemExit(f"File not found: {CSV}")

    df = pd.read_csv(CSV, usecols=["location_id", "observation_date", *FIELDS, "data_source"])
    df["observation_date"] = pd.to_datetime(df["observation_date"]).dt.date
    df = df.astype(object).where(df.notna(), None)

    db = SessionLocal()
    try:
        known = set(db.scalars(select(Location.location_id)).all())
        if not known:
            raise SystemExit("No locations in the database. Run scripts/setup_database.py first.")

        rows = [r for r in df.to_dict("records") if int(r["location_id"]) in known]
        skipped = len(df) - len(rows)
        now = datetime.utcnow()

        for start in range(0, len(rows), 1000):
            batch = [
                {**r, "location_id": int(r["location_id"]), "created_at": now}
                for r in rows[start:start + 1000]
            ]
            stmt = insert(WeatherObservation).values(batch)
            stmt = stmt.on_duplicate_key_update(
                **{f: stmt.inserted[f] for f in FIELDS}
            )
            db.execute(stmt)
        db.commit()
        print(f"Imported/updated {len(rows)} daily weather rows.")
        if skipped:
            print(f"Skipped {skipped} rows for locations not in the database.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
