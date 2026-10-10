
from datetime import datetime
from pathlib import Path
import math

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "haor_model" / "haor_flood_model.joblib"

FEATURE_COLUMNS = [
    "VV",
    "VH",
    "vv_vh_ratio",
    "rainfall",
    "soil_moisture",
    "temp",
    "wind",
    "slope",
    "twi",
    "rain_24h",
    "ndwi",
    "upstream_vv",
    "rain_96h",
    "temp_anomaly",
]


def predict_haor(features: dict) -> dict:
    """Predict using the Haor research model and its trained preprocessing."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Haor model not found at {MODEL_PATH}")

    missing = [name for name in FEATURE_COLUMNS if name not in features]
    if missing:
        raise ValueError(
            "Missing required features: " + ", ".join(missing)
        )

    try:
        values = {
            name: float(features[name])
            for name in FEATURE_COLUMNS
        }
    except (TypeError, ValueError):
        raise ValueError("All 14 features must be numeric.")

    # NaN is allowed because the trained model pipeline uses imputation.
    # Infinite values are not valid model inputs.
    if any(math.isinf(value) for value in values.values()):
        raise ValueError("Features cannot contain infinity.")

    model_bundle = joblib.load(MODEL_PATH)
    model = model_bundle["model"]

    columns = model_bundle.get("feature_columns", FEATURE_COLUMNS)
    X = pd.DataFrame([values], columns=columns)

    probabilities = model.predict_proba(X)[0]
    classes = list(model.classes_)

    if 1 not in classes:
        raise ValueError("The model does not contain the flood class (1).")

    flood_index = classes.index(1)
    probability = float(probabilities[flood_index])

    if probability >= 0.70:
        level = "HIGH"
    elif probability >= 0.40:
        level = "MODERATE"
    else:
        level = "LOW"

    return {
        "prediction_time": datetime.utcnow(),
        "flood_probability": probability,
        "risk_level": level,
        "model_name": model_bundle.get(
            "model_name",
            "Haor flood-event baseline Random Forest",
        ),
        "model_version": model_bundle.get(
            "model_version",
            "local-retrained",
        ),
        "scope": "Haor dataset only; research demonstration",
        "warning": (
            "Experimental result from a small dataset. "
            "Not a validated operational flood forecast."
        ),
    }
