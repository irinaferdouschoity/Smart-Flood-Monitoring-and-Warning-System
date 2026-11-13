from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import Location, SatellitePrecipitation
from backend.nasa.imerg import fetch_nearest_precipitation


db = SessionLocal()

# Get the most recent period.
# IMERG Final has a processing delay, so don't request today's data.
end = datetime.now(timezone.utc) - timedelta(days=1)
start = end - timedelta(days=7)

try:

    locations = db.scalars(
        select(Location)
    ).all()

    for loc in locations:

        try:

            rows = fetch_nearest_precipitation(
                float(loc.latitude),
                float(loc.longitude),
                start,
                end
            )

            inserted = 0

            for r in rows:

                t = r.get("observation_time")

                if isinstance(t, str):
                    t = datetime.fromisoformat(
                        t.replace("Z", "+00:00")
                    )

                if t is not None and t.tzinfo is not None:
                    t = t.replace(tzinfo=None)

                # Skip missing precipitation values
                if r.get("precipitation") is None:
                    continue

                db.add(
                    SatellitePrecipitation(
                        location_id=loc.location_id,
                        observation_time=t,
                        precipitation=float(
                            r["precipitation"]
                        ),
                        latitude=float(r["latitude"]),
                        longitude=float(r["longitude"]),
                        dataset=r["dataset"],
                        data_source=r["data_source"],
                        created_at=datetime.utcnow()
                    )
                )

                inserted += 1

            db.commit()

            print(
                f"{loc.location_name}: "
                f"{inserted} IMERG records inserted"
            )

        except Exception as e:

            db.rollback()

            print(
                f"[ERROR] "
                f"{loc.location_name}: {e}"
            )

finally:

    db.close()
