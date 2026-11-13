"""Train the 64-district flood model from data/bd_district_training_dataset.csv.

    python district_model/build_dataset.py            # once (creates the CSV)
    python district_model/train_district_model.py     # 3-day-ahead flood warning
    python district_model/train_district_model.py --horizon 1
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd

from district_model.pipeline import (feature_columns, leave_one_year_out,
                                     target_from_flag, train_and_evaluate)

DATASET_CSV = ROOT / "data" / "bd_district_training_dataset.csv"
OUT_MODEL = ROOT / "district_model" / "district_flood_model.joblib"
OUT_METRICS = ROOT / "district_model" / "district_metrics.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=3, help="warn for floods in the next N days")
    args = ap.parse_args()

    if not DATASET_CSV.exists():
        raise SystemExit("Dataset not found. Run first:  python district_model/build_dataset.py")

    df = pd.read_csv(DATASET_CSV, parse_dates=["date"], low_memory=False)
    data = target_from_flag(df[["location_id", "date", "flooded"] + feature_columns(df)], args.horizon)
    print(f"Training rows: {len(data):,}  flood-warning rows: {int(data['target'].sum()):,}")

    model, cols, metrics = train_and_evaluate(data, horizon=args.horizon)
    print("\nLeave-one-year-out check (each flood year is held out and predicted):")
    loyo = leave_one_year_out(data, horizon=args.horizon)
    for r in loyo:
        print(f"  {r['held_out_year']}: model PR-AUC {r['model_pr_auc']:.3f} vs rain-rule {r['baseline_rain3d_pr_auc']:.3f}"
              f"  |  ROC-AUC {r['model_roc_auc']:.3f} vs {r['baseline_rain3d_roc_auc']:.3f}  ({r['flood_rows']} flood rows)")
    metrics["leave_one_year_out"] = loyo

    joblib.dump({"model": model, "features": cols, "horizon_days": args.horizon,
                 "metrics": metrics}, OUT_MODEL)
    OUT_METRICS.write_text(json.dumps(metrics, indent=2))
    print("\nHold-out test (most recent period):")
    print(json.dumps({k: v for k, v in metrics.items() if k != "leave_one_year_out"}, indent=2))
    print(f"\nSaved {OUT_MODEL.name} and {OUT_METRICS.name}")
    print("The model is only useful if it beats the simple rain-rule baseline above.")


if __name__ == "__main__":
    main()
