"""Add all 64 districts of Bangladesh to the `locations` table.

    python scripts/setup_bd_districts.py

District points are approximate district centres (see data/bangladesh_districts.csv).
Dhaka reuses the existing location_id 1. Safe to run repeatedly: only missing
districts are added, nothing existing is changed or deleted.
"""
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import Location

CSV = Path(__file__).resolve().parents[1] / "data" / "bangladesh_districts.csv"


def main():
    districts = pd.read_csv(CSV)
    db = SessionLocal()
    try:
        existing = set(db.scalars(select(Location.location_id)).all())
        added = 0
        for row in districts.itertuples():
            if int(row.location_id) in existing:
                continue
            db.add(Location(
                location_id=int(row.location_id),
                location_name=row.district,
                country="Bangladesh",
                latitude=float(row.latitude),
                longitude=float(row.longitude),
                created_at=datetime.utcnow(),
            ))
            added += 1
        db.commit()
        print(f"Added {added} districts ({len(districts) - added} already existed).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
