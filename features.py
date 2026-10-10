
import pandas as pd

FEATURE_COLUMNS = [
    "rain_24h",
    "rain_3day",
    "rain_7day",
    "temperature_avg",
    "temperature_max",
    "temperature_min",
    "humidity",
    "dew_point",
    "wind_speed",
    "surface_pressure",
    "latitude",
    "longitude",
]


def add_features(df):
    df = df.sort_values(
        ["location_id", "observation_date"]
    ).copy()

    df["precipitation"] = pd.to_numeric(
        df["precipitation"], errors="coerce"
    )

    grouped = df.groupby("location_id")["precipitation"]

    df["rain_24h"] = grouped.transform(
        lambda s: s.rolling(1, min_periods=1).sum()
    )
    df["rain_3day"] = grouped.transform(
        lambda s: s.rolling(3, min_periods=3).sum()
    )
    df["rain_7day"] = grouped.transform(
        lambda s: s.rolling(7, min_periods=7).sum()
    )

    return df


def build_training_dataset(weather, floods):
    weather_features = add_features(weather)

    flood_labels = floods.copy()
    flood_labels["event_date"] = pd.to_datetime(
        flood_labels["event_date"]
    ).dt.date

    # Keep only dates with explicitly recorded flood labels.
    # Missing flood records remain unknown, not negative.
    labeled = weather_features.merge(
        flood_labels[
            ["location_id", "event_date", "flood_occurred"]
        ],
        left_on=["location_id", "observation_date"],
        right_on=["location_id", "event_date"],
        how="inner",
        validate="many_to_many",
    )

    labeled["flood_occurred"] = (
        labeled["flood_occurred"].astype(int)
    )

    return labeled.dropna(
        subset=FEATURE_COLUMNS + ["flood_occurred"]
    )
