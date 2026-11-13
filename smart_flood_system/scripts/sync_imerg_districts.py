"""Download daily NASA IMERG rainfall for all 64 Bangladesh districts into MySQL.

    python scripts/setup_bd_districts.py        (once, adds the districts)
    python scripts/sync_imerg_districts.py      (downloads IMERG)

Uses NASA POWER's daily IMERG precipitation (parameter IMERG_PRECTOT, mm/day,
0.1 degree GPM IMERG). No Earthdata login or big file downloads are needed.
Resumable: run it again and it continues from the newest stored day.

Options:
    --start 2015-01-01   first day to download (default 2015-01-01)
    --end   2026-11-01   last day (default: yesterday)
    --ids 101 102        only these location_ids
    --community SB       POWER community name for the IMERG parameter
"""
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import requests
from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert

from backend.config import settings
from backend.database import SessionLocal
from backend.models import Location, SatellitePrecipitation

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
DATASET = "IMERG daily (NASA POWER)"
CSV = Path(__file__).resolve().parents[1] / "data" / "bangladesh_districts.csv"


def year_chunks(start, end):
    cur = start
    while cur <= end:
        stop = min(date(cur.year, 12, 31), end)
        yield cur, stop
        cur = stop + timedelta(days=1)


def fetch_imerg(lat, lon, start, end, community):
    params = {
        "parameters": "IMERG_PRECTOT",
        "community": community,
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    last_error = None
    for attempt in range(1, 4):
        try:
            r = requests.get(POWER_URL, params=params, timeout=settings.nasa_power_timeout)
            if r.status_code == 422:
                raise SystemExit(
                    "NASA POWER rejected the request (422). The IMERG parameter or community "
                    f"name may have changed. Server said: {r.text[:300]}\n"
                    "Try --community AG, or check https://power.larc.nasa.gov/parameters/"
                )
            r.raise_for_status()
            series = r.json().get("properties", {}).get("parameter", {}).get("IMERG_PRECTOT")
            if series is None:
                raise ValueError("response has no IMERG_PRECTOT values")
            return series
        except SystemExit:
            raise
        except Exception as exc:
            last_error = exc
            time.sleep(2 * attempt)
    raise RuntimeError(f"failed after 3 tries: {last_error}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2015-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--ids", nargs="*", type=int)
    ap.add_argument("--community", default="SB")
    args = ap.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else date.today() - timedelta(days=1)

    district_ids = set(pd.read_csv(CSV)["location_id"].astype(int))
    if args.ids:
        district_ids &= set(args.ids)

    db = SessionLocal()
    try:
        locations = [
            l for l in db.scalars(select(Location).order_by(Location.location_id)).all()
            if l.location_id in district_ids
        ]
        if not locations:
            raise SystemExit("No districts in the database. Run scripts/setup_bd_districts.py first.")

        total = 0
        for n, loc in enumerate(locations, 1):
            newest = db.scalar(
                select(func.max(SatellitePrecipitation.observation_time)).where(
                    SatellitePrecipitation.location_id == loc.location_id,
                    SatellitePrecipitation.dataset == DATASET,
                )
            )
            loc_start = start if newest is None else max(start, newest.date() - timedelta(days=7))
            if loc_start > end:
                print(f"[{n}/{len(locations)}] {loc.location_name}: up to date")
                continue

            rows_written = 0
            try:
                for a, b in year_chunks(loc_start, end):
                    series = fetch_imerg(float(loc.latitude), float(loc.longitude), a, b, args.community)
                    rows = []
                    for day, value in series.items():
                        if value is None or float(value) <= -990:
                            continue  # NASA fill value = no data yet
                        rows.append({
                            "location_id": loc.location_id,
                            "observation_time": datetime.strptime(day, "%Y%m%d"),
                            "precipitation": float(value),
                            "latitude": float(loc.latitude),
                            "longitude": float(loc.longitude),
                            "dataset": DATASET,
                            "data_source": "NASA POWER",
                            "created_at": datetime.utcnow(),
                        })
                    for i in range(0, len(rows), 500):
                        stmt = insert(SatellitePrecipitation).values(rows[i:i + 500])
                        db.execute(stmt.on_duplicate_key_update(precipitation=stmt.inserted.precipitation))
                    db.commit()
                    rows_written += len(rows)
                    time.sleep(0.5)  # be polite to the NASA server
                total += rows_written
                print(f"[{n}/{len(locations)}] {loc.location_name}: {rows_written} days")
            except Exception as exc:
                db.rollback()
                print(f"[{n}/{len(locations)}] {loc.location_name}: ERROR {exc}")
        print(f"Done. {total} daily IMERG values written.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
