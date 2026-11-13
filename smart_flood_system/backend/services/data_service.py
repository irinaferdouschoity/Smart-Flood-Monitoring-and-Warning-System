from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.dialects.mysql import insert

from ..config import settings
from ..database import SessionLocal
from ..models import Location, WeatherObservation
from ..nasa.power import fetch_power_daily
from ..ml.features import add_features


def upsert_power_data(db, loc, start_date, end_date):

    df = fetch_power_daily(
        float(loc.latitude),
        float(loc.longitude),
        start_date,
        end_date
    )

    weather_fields = [
        "precipitation",
        "temperature_avg",
        "temperature_max",
        "temperature_min",
        "humidity",
        "dew_point",
        "wind_speed",
        "surface_pressure",
    ]

    inserted = 0

    for r in df.to_dict("records"):

        # Convert Pandas NaN to real Python None
        values = {}

        for field in weather_fields:
            value = r.get(field)

            if pd.isna(value):
                values[field] = None
            else:
                values[field] = float(value)

        # If NASA returned no usable values for this day,
        # don't insert a completely empty observation.
        if all(values[field] is None for field in weather_fields):
            print(
                f"[SKIP] No NASA POWER data for "
                f"{r['observation_date']}"
            )
            continue

        q = insert(WeatherObservation).values(
            location_id=loc.location_id,
            observation_date=r["observation_date"],
            precipitation=values["precipitation"],
            temperature_avg=values["temperature_avg"],
            temperature_max=values["temperature_max"],
            temperature_min=values["temperature_min"],
            humidity=values["humidity"],
            dew_point=values["dew_point"],
            wind_speed=values["wind_speed"],
            surface_pressure=values["surface_pressure"],
            data_source="NASA POWER",
            created_at=datetime.utcnow(),
        )

        q = q.on_duplicate_key_update(
            precipitation=q.inserted.precipitation,
            temperature_avg=q.inserted.temperature_avg,
            temperature_max=q.inserted.temperature_max,
            temperature_min=q.inserted.temperature_min,
            humidity=q.inserted.humidity,
            dew_point=q.inserted.dew_point,
            wind_speed=q.inserted.wind_speed,
            surface_pressure=q.inserted.surface_pressure,
        )

        db.execute(q)
        inserted += 1

    db.commit()

    return inserted


def latest_features(db, location_id):

    rows = db.scalars(
        select(WeatherObservation)
        .where(
            WeatherObservation.location_id == location_id
        )
        .order_by(
            WeatherObservation.observation_date
        )
    ).all()

    if len(rows) < 7:
        raise ValueError(
            "At least 7 daily observations are required "
            "for rolling rainfall features."
        )

    loc = db.get(Location, location_id)

    df = pd.DataFrame([
        {
            "location_id": r.location_id,
            "observation_date": r.observation_date,
            "precipitation": r.precipitation,
            "temperature_avg": r.temperature_avg,
            "temperature_max": r.temperature_max,
            "temperature_min": r.temperature_min,
            "humidity": r.humidity,
            "dew_point": r.dew_point,
            "wind_speed": r.wind_speed,
            "surface_pressure": r.surface_pressure,
            "latitude": float(loc.latitude),
            "longitude": float(loc.longitude),
        }
        for r in rows
    ])

    x = add_features(df).iloc[-1]

    return {
        "rain_24h": float(x["rain_24h"]),
        "rain_3day": float(x["rain_3day"]),
        "rain_7day": float(x["rain_7day"]),
        "temperature_avg": float(x["temperature_avg"]),
        "temperature_max": float(x["temperature_max"]),
        "temperature_min": float(x["temperature_min"]),
        "humidity": float(x["humidity"]),
        "dew_point": float(x["dew_point"]),
        "wind_speed": float(x["wind_speed"]),
        "surface_pressure": float(x["surface_pressure"]),
        "latitude": float(x["latitude"]),
        "longitude": float(x["longitude"]),
    }

# ---------------------------------------------------------------------------
# Automatic NASA POWER download
# ---------------------------------------------------------------------------

REFRESH_DAYS = 7  # re-fetch the last week: NASA fills recent days in late


def _year_chunks(start, end):
    """Split [start, end] into calendar-year pieces (keeps each request small)."""
    chunks = []
    current = start
    while current <= end:
        chunk_end = min(date(current.year, 12, 31), end)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return chunks


def sync_power_data(db, loc):
    """Download every missing day for one location straight into MySQL.

    - New/empty location: downloads from settings.history_start (2020-01-01).
    - Otherwise: continues from the newest stored day (minus 7 days so late
      NASA corrections are picked up) up to yesterday.
    Existing days are updated, never duplicated. Returns rows written.
    """
    end = date.today() - timedelta(days=1)

    latest = db.scalar(
        select(func.max(WeatherObservation.observation_date)).where(
            WeatherObservation.location_id == loc.location_id,
            WeatherObservation.data_source == "NASA POWER",
        )
    )

    if latest is None:
        start = date.fromisoformat(settings.history_start)
    else:
        start = latest - timedelta(days=REFRESH_DAYS)

    if start > end:
        return 0

    total = 0
    for chunk_start, chunk_end in _year_chunks(start, end):
        total += upsert_power_data(db, loc, chunk_start, chunk_end)
    return total


def sync_locations(db):
    """Sync all locations. One failing city never stops the others."""
    results = []
    for loc in db.scalars(select(Location)).all():
        try:
            count = sync_power_data(db, loc)
            results.append(
                {"location_id": loc.location_id, "status": "success", "records": count}
            )
        except Exception as exc:
            db.rollback()
            results.append(
                {"location_id": loc.location_id, "status": "error", "error": str(exc)}
            )
    return results


def sync_all_locations():
    """Same as sync_locations but opens its own database session
    (used by the background auto-sync)."""
    db = SessionLocal()
    try:
        return sync_locations(db)
    finally:
        db.close()
