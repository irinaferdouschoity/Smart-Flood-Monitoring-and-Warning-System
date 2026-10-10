from pathlib import Path
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

BASE = Path(__file__).resolve().parent
DATA = BASE / "haor_flood_events_cleaned.csv"
MODEL_OUT = BASE / "haor_flood_model.joblib"
FEATURES = [
    "VV", "VH", "vv_vh_ratio", "rainfall", "soil_moisture", "temp",
    "wind", "slope", "twi", "rain_24h", "ndwi", "upstream_vv",
    "rain_96h", "temp_anomaly",
]

def main():
    df = pd.read_csv(DATA, parse_dates=["date"])
    required = ["flood_label"] + FEATURES
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df["flood_label"] = pd.to_numeric(df["flood_label"], errors="raise").astype(int)
    if set(df["flood_label"].unique()) != {0, 1}:
        raise ValueError("Need both label classes 0 and 1; refusing to train.")
    X, y = df[FEATURES], df["flood_label"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(
            n_estimators=300, class_weight="balanced", random_state=42
        )),
    ])
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    print("Rows:", len(df), "| labels:", y.value_counts().sort_index().to_dict())
    print("Train/test:", len(X_train), "/", len(X_test))
    print("Accuracy:", round(accuracy_score(y_test, pred), 3))
    print("Balanced accuracy:", round(balanced_accuracy_score(y_test, pred), 3))
    print("Confusion matrix [true rows 0,1; predicted columns 0,1]:")
    print(confusion_matrix(y_test, pred))
    print(classification_report(y_test, pred, zero_division=0))
    if y_test.nunique() == 2:
        print("ROC-AUC:", round(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]), 3))
    bundle = {
        "model": model,
        "feature_columns": FEATURES,
        "model_version": "haor-baseline-2026-10-10",
        "label_scope": "Haor-region event samples; not validated for other cities",
    }
    joblib.dump(bundle, MODEL_OUT)
    print("Saved:", MODEL_OUT)
    print("WARNING: small dataset; random split metrics are preliminary only.")
    print("This model requires the 14 listed satellite/environmental features.")
    print("Do not connect it directly to a backend that only supplies NASA POWER weather fields.")

if __name__ == "__main__":
    main()
