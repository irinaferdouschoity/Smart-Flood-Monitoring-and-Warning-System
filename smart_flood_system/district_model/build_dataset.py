"""Build ONE CSV with everything: IMERG rainfall, weather, flood days and event names.

    python district_model/build_dataset.py

Needs (see README):  setup_bd_districts.py  ->  sync_imerg_districts.py  ->  build_flood_labels.py
Writes data/bd_district_training_dataset.csv  (one row per district per day).

Columns (main ones)
  district, division, date
  rain_1d ... rain_30d     IMERG rainfall totals (mm) over the last 1..30 days
  rain_prior_8_30d, wet_days_7d, rain_max_7d      how wet the previous weeks were
  temperature_avg, humidity, wind_speed, surface_pressure     NASA POWER weather
  season_sin, season_cos   time of year (monsoon)
  flooded                  1 = a documented flood event covers this district-day
  event_id, label_confidence   which event(s), and how sure the dates are
  flood_next_3d            1 = flooding within the next 3 days (the prediction target)
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from district_model.pipeline import assemble_dataset

DISTRICTS_CSV = ROOT / "data" / "bangladesh_districts.csv"
LABELS_CSV = ROOT / "data" / "flood_labels" / "bd_district_flood_labels.csv"
OUT = ROOT / "data" / "bd_district_training_dataset.csv"
DATASET = "IMERG daily (NASA POWER)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=3)
    ap.add_argument("--only-labelled-districts", action="store_true",
                    help="keep only districts that have at least one documented flood")
    args = ap.parse_args()

    from backend.database import engine  # imported here so the file can be tested without MySQL

    if not LABELS_CSV.exists():
        raise SystemExit("Run first:  python scripts/build_flood_labels.py")

    districts = pd.read_csv(DISTRICTS_CSV)
    labels = pd.read_csv(LABELS_CSV)
    ids = ",".join(str(int(i)) for i in districts["location_id"])

    rain = pd.read_sql(
        f"SELECT location_id, observation_time AS date, precipitation AS rain "
        f"FROM satellite_precipitation WHERE dataset = '{DATASET}' AND location_id IN ({ids})", engine)
    if rain.empty:
        raise SystemExit("No IMERG rainfall in MySQL. Run scripts/sync_imerg_districts.py first.")
    rain["rain"] = rain["rain"].astype(float)

    weather = pd.read_sql(
        f"SELECT location_id, observation_date AS date, temperature_avg, humidity, wind_speed, "
        f"surface_pressure FROM weather_observations WHERE data_source = 'NASA POWER' "
        f"AND location_id IN ({ids})", engine)
    for c in ["temperature_avg", "humidity", "wind_speed", "surface_pressure"]:
        weather[c] = weather[c].astype(float)

    if args.only_labelled_districts:
        rain = rain[rain["location_id"].isin(labels["location_id"].unique())]

    df = assemble_dataset(rain, weather, labels, districts, horizon=args.horizon)
    df.to_csv(OUT, index=False)
    print(f"Saved {OUT}")
    print(f"{len(df):,} district-days, {df['district'].nunique()} districts, "
          f"{df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Flood days: {int(df['flooded'].sum()):,}  ({df['flooded'].mean():.2%} of all rows)")


if __name__ == "__main__":
    main()
