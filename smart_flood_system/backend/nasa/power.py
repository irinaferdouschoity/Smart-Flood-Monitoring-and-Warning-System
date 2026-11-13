from datetime import date
import requests
import pandas as pd

from ..config import settings

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

PARAMETERS = [
    "PRECTOTCORR",
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M",
    "T2MDEW",
    "WS2M",
    "PS",
]


def fetch_power_daily(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date
):
    params = {
        "parameters": ",".join(PARAMETERS),
        "community": "AG",
        "longitude": round(longitude, 4),
        "latitude": round(latitude, 4),
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON",
    }

    response = requests.get(
        POWER_URL,
        params=params,
        timeout=settings.nasa_power_timeout
    )

    response.raise_for_status()

    result = response.json()

    data = result.get("properties", {}).get("parameter", {})

    if not data:
        raise ValueError(
            "NASA POWER returned no parameter data."
        )

    # Make sure the requested parameters actually exist
    missing_parameters = [
        p for p in PARAMETERS
        if p not in data
    ]

    if missing_parameters:
        raise ValueError(
            f"NASA POWER response is missing parameters: "
            f"{missing_parameters}"
        )

    # Get all available dates
    days = sorted(
        set().union(
            *[
                values.keys()
                for values in data.values()
            ]
        )
    )

    if not days:
        raise ValueError(
            "NASA POWER returned no dates."
        )

    def get_value(parameter, day):
        value = data[parameter].get(day)

        # NASA uses -999 for missing values
        if value is None or value == -999:
            return None

        try:
            value = float(value)

            # Protect MySQL from NaN / infinity
            if pd.isna(value):
                return None

            return value

        except (TypeError, ValueError):
            return None

    records = []

    for day in days:

        record = {
            "observation_date": pd.to_datetime(day).date(),

            "precipitation": get_value(
                "PRECTOTCORR", day
            ),

            "temperature_avg": get_value(
                "T2M", day
            ),

            "temperature_max": get_value(
                "T2M_MAX", day
            ),

            "temperature_min": get_value(
                "T2M_MIN", day
            ),

            "humidity": get_value(
                "RH2M", day
            ),

            "dew_point": get_value(
                "T2MDEW", day
            ),

            "wind_speed": get_value(
                "WS2M", day
            ),

            "surface_pressure": get_value(
                "PS", day
            ),

            "data_source": "NASA POWER",
        }

        records.append(record)

    df = pd.DataFrame(records)

    # IMPORTANT:
    # Do not send NaN values to MySQL.
    df = df.where(pd.notna(df), None)

    # Show us how much actual NASA data we received
    print(
        f"NASA POWER: {len(df)} days received "
        f"for ({latitude}, {longitude})"
    )

    print(
        df.head(3).to_string(index=False)
    )

    return df