
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import Location, SatellitePrecipitation
from backend.nasa.imerg import fetch_nearest_precipitation


def save_imerg_for_location(
    location_id: int,
    start_date: date,
    end_date: date,
) -> int:
    """Fetch IMERG daily data and save it to MySQL."""

    saved_count = 0
    db = SessionLocal()

    try:
        location = db.get(Location, location_id)

        if location is None:
            raise ValueError(
                f"Location ID {location_id} was not found."
            )

        latitude = float(location.latitude)
        longitude = float(location.longitude)

        print(
            f"\nLocation: {location.location_name}, "
            f"{location.country}"
        )
        print(f"Coordinates: {latitude}, {longitude}")

        start = datetime.combine(
            start_date, time.min, tzinfo=timezone.utc
        )
        end = datetime.combine(
            end_date, time.max, tzinfo=timezone.utc
        )

        records = fetch_nearest_precipitation(
            latitude=latitude,
            longitude=longitude,
            start=start,
            end=end,
        )

        for record in records:
            if record["precipitation"] is None:
                print(
                    "[SKIP] Missing precipitation for "
                    f"{record['observation_time']}"
                )
                continue

            observation_date = date.fromisoformat(
                record["observation_time"]
            )

            # Store the daily observation at midnight.
            observation_time = datetime.combine(
                observation_date, time.min
            )

            dataset = record["dataset"]

            existing = db.scalar(
                select(SatellitePrecipitation).where(
                    SatellitePrecipitation.location_id
                    == location_id,
                    SatellitePrecipitation.observation_time
                    == observation_time,
                    SatellitePrecipitation.dataset == dataset,
                )
            )

            precipitation = Decimal(
                str(record["precipitation"])
            )

            if existing:
                # Update an existing record instead of duplicating it.
                existing.precipitation = precipitation
                existing.latitude = Decimal(
                    str(record["latitude"])
                )
                existing.longitude = Decimal(
                    str(record["longitude"])
                )
                existing.data_source = record["data_source"]

                print(
                    f"[UPDATE] {observation_date}: "
                    f"{precipitation}"
                )
            else:
                db.add(
                    SatellitePrecipitation(
                        location_id=location_id,
                        observation_time=observation_time,
                        precipitation=precipitation,
                        latitude=Decimal(
                            str(record["latitude"])
                        ),
                        longitude=Decimal(
                            str(record["longitude"])
                        ),
                        dataset=dataset,
                        data_source=record["data_source"],
                    )
                )

                print(
                    f"[INSERT] {observation_date}: "
                    f"{precipitation}"
                )

            saved_count += 1

        db.commit()

        print(
            f"\nFinished. Records inserted or updated: "
            f"{saved_count}"
        )

        return saved_count

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Fetch NASA IMERG data and save it to MySQL."
    )

    parser.add_argument(
        "--location-id",
        type=int,
        default=1,
        help="Location ID from the locations table (default: 1).",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End date in YYYY-MM-DD format.",
    )

    args = parser.parse_args()

    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)

    if end_date < start_date:
        parser.error("--end must not be earlier than --start")

    save_imerg_for_location(
        location_id=args.location_id,
        start_date=start_date,
        end_date=end_date,
    )


if __name__ == "__main__":
    main()