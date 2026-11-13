
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np


def _earthaccess():
    """Import earthaccess only when IMERG is actually used, so the rest of the
    app runs without it. Install it with: pip install -r requirements-optional.txt"""
    try:
        import earthaccess
    except ImportError as exc:
        raise RuntimeError(
            "IMERG needs the optional 'earthaccess' package. "
            "Run: pip install -r requirements-optional.txt"
        ) from exc
    return earthaccess


# NASA GPM IMERG Final Daily V07
DEFAULT_SHORT_NAME = "GPM_3IMERGDF"
DEFAULT_VERSION = "07"

DOWNLOAD_DIR = Path("data") / "imerg_downloads"


def authenticate_earthdata():
    """Authenticate using credentials in the local _netrc file."""

    auth = _earthaccess().login(strategy="netrc")

    if not auth or not auth.authenticated:
        raise RuntimeError(
            "Earthdata authentication failed. "
            "Check your local Windows _netrc credentials."
        )

    return auth


def nearest_value(path, latitude, longitude):
    """
    Extract precipitation from the IMERG grid cell nearest
    to the requested latitude and longitude.

    Returns precipitation as a float, or None if the grid
    cell contains missing or invalid data.
    """

    with h5py.File(path, "r") as file:
        if "precipitation" not in file:
            raise ValueError(
                "No precipitation dataset found in IMERG file."
            )

        if "lat" not in file or "lon" not in file:
            raise ValueError(
                "Latitude or longitude coordinates are missing."
            )

        dataset = file["precipitation"]
        precipitation = np.asarray(dataset[...]).squeeze()
        lats = np.asarray(file["lat"][:]).squeeze()
        lons = np.asarray(file["lon"][:]).squeeze()

        if precipitation.ndim != 2:
            raise ValueError(
                "Unexpected precipitation dimensions: "
                f"{precipitation.shape}"
            )

        if lats.ndim != 1 or lons.ndim != 1:
            raise ValueError(
                "Expected one-dimensional latitude and longitude."
            )

        # Find the nearest longitude, accounting for wraparound.
        lon_difference = np.abs(
            (lons - longitude + 180) % 360 - 180
        )
        lon_index = int(np.argmin(lon_difference))

        # Find the nearest latitude.
        lat_index = int(np.argmin(np.abs(lats - latitude)))

        # Support either common ordering of the two grid dimensions.
        if precipitation.shape == (len(lons), len(lats)):
            value = precipitation[lon_index, lat_index]

        elif precipitation.shape == (len(lats), len(lons)):
            value = precipitation[lat_index, lon_index]

        else:
            raise ValueError(
                "Coordinate dimensions do not match precipitation: "
                f"precipitation={precipitation.shape}, "
                f"latitude={lats.shape}, longitude={lons.shape}"
            )

        value = float(value)

        # Check common missing-value representations.
        if not np.isfinite(value):
            return None

        fill_value = dataset.attrs.get("_FillValue")

        if fill_value is not None:
            fill_value = float(np.asarray(fill_value).squeeze())

            if np.isclose(value, fill_value):
                return None

        if value < 0:
            return None

        return value


def download_granule(granule, output_dir=DOWNLOAD_DIR):
    """Download one granule using Earthaccess."""

    authenticate_earthdata()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = _earthaccess().download(
        [granule],
        str(output_dir),
    )

    if not downloaded:
        raise RuntimeError(
            "Earthaccess did not download an IMERG file."
        )

    file_path = Path(downloaded[0])

    if not file_path.exists():
        raise FileNotFoundError(
            f"Downloaded IMERG file was not found: {file_path}"
        )

    return file_path


def extract_observation_date(file_path, granule=None):
    """
    Extract the daily observation date from the filename.

    IMERG daily filenames commonly contain a date token such
    as 3IMERG.20250925-S000000-E235959....
    """

    filename = Path(file_path).name

    marker = "3IMERG."

    if marker in filename:
        date_token = filename.split(marker, 1)[1][:8]

        try:
            return datetime.strptime(
                date_token, "%Y%m%d"
            ).date().isoformat()
        except ValueError:
            pass

    # Fall back to the granule metadata if available.
    if granule is not None:
        try:
            metadata = granule.__dict__

            for key in ("time_start", "start_time"):
                value = metadata.get(key)

                if value:
                    parsed = datetime.fromisoformat(
                        str(value).replace("Z", "+00:00")
                    )
                    return parsed.date().isoformat()

        except (AttributeError, TypeError, ValueError):
            pass

    raise ValueError(
        f"Could not determine the observation date from {filename}"
    )


def fetch_nearest_precipitation(
    latitude,
    longitude,
    start,
    end,
):
    """
    Search and download available IMERG Final Daily V07 granules.

    Args:
        latitude: Requested latitude.
        longitude: Requested longitude.
        start: Start datetime or date boundary.
        end: End datetime or date boundary.

    Returns:
        A list of dictionaries for MySQL insertion.

    Note:
        Only dates for which granules are returned by NASA are
        included. Missing days are not fabricated.
    """

    # Treat naive datetimes as UTC.
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    if end < start:
        raise ValueError(
            "The end date must not precede the start date."
        )

    authenticate_earthdata()

    print(
        f"[IMERG] Searching {DEFAULT_SHORT_NAME}, "
        f"version {DEFAULT_VERSION}"
    )
    print(f"[IMERG] Requested period: {start} to {end}")

    # count=-1 requests all matching granules instead of limiting
    # the search to the first 100.
    granules = _earthaccess().search_data(
        short_name=DEFAULT_SHORT_NAME,
        version=DEFAULT_VERSION,
        temporal=(start, end),
        count=-1,
    )

    if not granules:
        print(
            "[IMERG] No granules found. The product may not "
            "be available for the requested period yet."
        )
        return []

    print(f"[IMERG] Granules found: {len(granules)}")

    output = []
    seen_dates = set()

    for index, granule in enumerate(granules, start=1):
        print(
            f"[IMERG] Processing granule "
            f"{index}/{len(granules)}"
        )

        try:
            file_path = download_granule(
                granule,
                DOWNLOAD_DIR,
            )

            observation_date = extract_observation_date(
                file_path,
                granule,
            )

            # Prevent duplicate dates within this result.
            if observation_date in seen_dates:
                print(
                    f"[IMERG] Duplicate date skipped: "
                    f"{observation_date}"
                )
                continue

            precipitation = nearest_value(
                file_path,
                latitude,
                longitude,
            )

            record = {
                "observation_time": observation_date,
                "precipitation": precipitation,
                "latitude": latitude,
                "longitude": longitude,
                "dataset": (
                    f"{DEFAULT_SHORT_NAME}_V{DEFAULT_VERSION}"
                ),
                "data_source": "NASA GPM IMERG / GES DISC",
            }

            output.append(record)
            seen_dates.add(observation_date)

            print(
                f"[IMERG] {observation_date}: "
                f"{precipitation}"
            )

        except Exception as exc:
            print(
                f"[IMERG ERROR] Granule "
                f"{index}/{len(granules)} failed: {exc}"
            )
            raise

    output.sort(
        key=lambda record: record["observation_time"]
    )

    print(
        f"[IMERG] Completed. Daily records returned: "
        f"{len(output)}"
    )

    return output