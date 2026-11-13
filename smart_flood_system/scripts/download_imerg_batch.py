
from datetime import date, datetime, time, timezone
from pathlib import Path
import argparse
import re
import sys

import earthaccess
import h5py
import numpy as np
from sqlalchemy import select, func
from sqlalchemy.dialects.mysql import insert as mysql_insert

# Allow imports from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import SessionLocal
from backend.models import Location, SatellitePrecipitation


SHORT_NAME = "GPM_3IMERGDF"
VERSION = "07"
DATASET_NAME = "GPM_3IMERGDF_V07"
DATA_SOURCE = "NASA GPM IMERG / GES DISC"
DOWNLOAD_DIR = PROJECT_ROOT / "data" / "imerg_downloads"


def observation_date_from_file(file_path):
    """Extract YYYYMMDD from a standard IMERG filename."""
    name = Path(file_path).name
    match = re.search(r"3IMERG\.(\d{8})-", name)

    if not match:
        match = re.search(r"3IMERG\.(\d{8})", name)

    if not match:
        raise ValueError(f"Cannot find date in filename: {name}")

    return datetime.strptime(match.group(1), "%Y%m%d").date()


def extract_nearest_rainfall(file_path, latitude, longitude):
    """Read daily precipitation at the nearest grid cell."""
    with h5py.File(file_path, "r") as file:
        for name in ("precipitation", "lat", "lon"):
            if name not in file:
                raise ValueError(
                    f"Missing dataset '{name}' in {Path(file_path).name}"
                )

        dataset = file["precipitation"]
        rainfall = np.asarray(dataset[...]).squeeze()
        latitudes = np.asarray(file["lat"][:]).squeeze()
        longitudes = np.asarray(file["lon"][:]).squeeze()

        if rainfall.ndim != 2:
            raise ValueError(
                f"Unexpected precipitation dimensions: {rainfall.shape}"
            )

        if latitudes.ndim != 1 or longitudes.ndim != 1:
            raise ValueError("Expected one-dimensional latitude and longitude")

        # Support longitude coordinates in either 0..360 or -180..180 format.
        longitude_difference = np.abs(
            (longitudes - longitude + 180) % 360 - 180
        )
        lon_index = int(np.argmin(longitude_difference))
        lat_index = int(np.argmin(np.abs(latitudes - latitude)))

        if rainfall.shape == (len(latitudes), len(longitudes)):
            value = rainfall[lat_index, lon_index]
        elif rainfall.shape == (len(longitudes), len(latitudes)):
            value = rainfall[lon_index, lat_index]
        else:
            raise ValueError(
                "Precipitation shape does not match latitude/longitude arrays: "
                f"{rainfall.shape}"
            )

        value = float(value)

        fill_value = dataset.attrs.get("_FillValue")
        if fill_value is not None:
            fill_value = float(np.asarray(fill_value).squeeze())
            if np.isclose(value, fill_value):
                return None

        if not np.isfinite(value) or value < 0:
            return None

        return value


def download_one(granule):
    """Download a single granule into the local download folder."""
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    result = earthaccess.download([granule], str(DOWNLOAD_DIR))
    if not result:
        raise RuntimeError("NASA Earthdata returned no downloaded file")

    path = Path(result[0])
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"Downloaded file is missing or empty: {path}")

    return path


def date_is_complete(db, observation_day, location_ids):
    """Return True when every location already has this dataset/date."""
    start = datetime.combine(observation_day, time.min)
    end = datetime.combine(observation_day, time.max)

    count = db.scalar(
        select(func.count(func.distinct(SatellitePrecipitation.location_id)))
        .where(
            SatellitePrecipitation.dataset == DATASET_NAME,
            SatellitePrecipitation.observation_time >= start,
            SatellitePrecipitation.observation_time <= end,
            SatellitePrecipitation.location_id.in_(location_ids),
        )
    )

    return count == len(location_ids)


def save_day(db, observation_day, locations, file_path):
    """Extract and upsert one daily file for all locations."""
    observation_time = datetime.combine(observation_day, time.min)
    rows = []

    for location in locations:
        rainfall = extract_nearest_rainfall(
            file_path,
            float(location.latitude),
            float(location.longitude),
        )

        rows.append({
            "location_id": location.location_id,
            "observation_time": observation_time,
            "precipitation": rainfall,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "dataset": DATASET_NAME,
            "data_source": DATA_SOURCE,
            "created_at": datetime.now(),
        })

    if not rows:
        return 0

    statement = mysql_insert(SatellitePrecipitation).values(rows)
    statement = statement.on_duplicate_key_update(
        precipitation=statement.inserted.precipitation,
        latitude=statement.inserted.latitude,
        longitude=statement.inserted.longitude,
        data_source=statement.inserted.data_source,
    )

    db.execute(statement)
    db.commit()
    return len(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Download daily NASA GPM IMERG data for all database locations."
    )
    parser.add_argument("--start", default="2025-08-01")
    parser.add_argument("--end", default="2025-08-31")
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep downloaded HDF5 files after processing.",
    )
    args = parser.parse_args()

    start_day = date.fromisoformat(args.start)
    end_day = date.fromisoformat(args.end)

    if end_day < start_day:
        parser.error("--end must not be earlier than --start")

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    print("Authenticating with NASA Earthdata...")
    auth = earthaccess.login(strategy="netrc")
    if not auth or not auth.authenticated:
        raise RuntimeError(
            "Earthdata authentication failed. Check your local _netrc setup."
        )

    db = SessionLocal()

    try:
        locations = db.scalars(
            select(Location).order_by(Location.location_id)
        ).all()

        if not locations:
            raise RuntimeError("No locations found in the locations table.")

        location_ids = [location.location_id for location in locations]

        print(f"Locations: {len(locations)}")
        for location in locations:
            print(
                f"  {location.location_id}: {location.location_name} "
                f"({location.latitude}, {location.longitude})"
            )

        # Search a little wider, then filter using dates in the filenames.
        search_start = datetime.combine(
            start_day, time.min, tzinfo=timezone.utc
        )
        search_end = datetime.combine(
            end_day, time.max, tzinfo=timezone.utc
        )

        print(f"Searching IMERG from {start_day} through {end_day}...")
        granules = earthaccess.search_data(
            short_name=SHORT_NAME,
            version=VERSION,
            temporal=(search_start, search_end),
            count=-1,
        )

        if not granules:
            print("No granules returned for this period.")
            return

        print(f"Granules returned: {len(granules)}")

        processed_dates = set()
        saved_records = 0
        skipped_dates = 0
        errors = 0

        for index, granule in enumerate(granules, start=1):
            file_path = None

            try:
                file_path = download_one(granule)
                observation_day = observation_date_from_file(file_path)

                if not (start_day <= observation_day <= end_day):
                    print(f"[SKIP] Outside requested dates: {observation_day}")
                    continue

                if observation_day in processed_dates:
                    continue

                if date_is_complete(db, observation_day, location_ids):
                    print(f"[SKIP] Already complete: {observation_day}")
                    skipped_dates += 1
                    processed_dates.add(observation_day)
                    continue

                number_saved = save_day(
                    db, observation_day, locations, file_path
                )

                saved_records += number_saved
                processed_dates.add(observation_day)

                print(
                    f"[{index}/{len(granules)}] {observation_day}: "
                    f"processed {number_saved} locations"
                )

            except Exception as exc:
                db.rollback()
                errors += 1
                print(f"[ERROR] Granule {index}: {exc}")

            finally:
                if file_path and not args.keep_files:
                    try:
                        file_path.unlink(missing_ok=True)
                    except OSError as exc:
                        print(f"[WARNING] Could not remove {file_path}: {exc}")

        print("\nBatch finished.")
        print(f"Dates processed: {len(processed_dates)}")
        print(f"Dates skipped as complete: {skipped_dates}")
        print(f"Location records inserted/updated: {saved_records}")
        print(f"Errors: {errors}")
        print(f"Download folder: {DOWNLOAD_DIR}")

    finally:
        db.close()


if __name__ == "__main__":
    main()