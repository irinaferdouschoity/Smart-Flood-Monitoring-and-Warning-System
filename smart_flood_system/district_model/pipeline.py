"""Feature building, labelling and training for the 64-district flood model.

Pure pandas / scikit-learn code (no database), so it can be tested on its own.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

RAIN_WINDOWS = (2, 3, 5, 7, 14, 30)
WEATHER_COLS = ["temperature_avg", "humidity", "wind_speed", "surface_pressure"]


def _district_features(g: pd.DataFrame) -> pd.DataFrame:
    """Features for ONE district. Every feature uses only today and earlier days."""
    g = g.sort_values("date").set_index("date")
    g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="D"))
    g.index.name = "date"
    rain = g["rain"]

    out = pd.DataFrame(index=g.index)
    out["rain_1d"] = rain
    for w in RAIN_WINDOWS:
        out[f"rain_{w}d"] = rain.rolling(w, min_periods=w).sum()
    out["rain_max_7d"] = rain.rolling(7, min_periods=7).max()
    out["wet_days_7d"] = (rain >= 1).astype(float).where(rain.notna()).rolling(7, min_periods=7).sum()
    # rain in days 8-30 before today = how wet the ground already was
    out["rain_prior_8_30d"] = out["rain_30d"] - out["rain_7d"]
    for c in WEATHER_COLS:
        if c in g.columns:
            out[c] = g[c]
    doy = out.index.dayofyear.to_numpy()
    out["season_sin"] = np.sin(2 * np.pi * doy / 365.25)  # monsoon seasonality
    out["season_cos"] = np.cos(2 * np.pi * doy / 365.25)
    out["location_id"] = g["location_id"].ffill().bfill().iloc[0]
    return out.reset_index()


def build_features(rain: pd.DataFrame, weather: pd.DataFrame | None = None) -> pd.DataFrame:
    """rain: location_id, date, rain (mm/day).  weather (optional): location_id, date + WEATHER_COLS."""
    data = rain.copy()
    data["date"] = pd.to_datetime(data["date"])
    if weather is not None and len(weather):
        w = weather.copy()
        w["date"] = pd.to_datetime(w["date"])
        data = data.merge(w, on=["location_id", "date"], how="left")
    parts = [_district_features(g) for _, g in data.groupby("location_id")]
    return pd.concat(parts, ignore_index=True)


def target_from_flag(df: pd.DataFrame, horizon: int = 3) -> pd.DataFrame:
    """df needs location_id, date, flooded (0/1 = district flooded on that day).

    target = 1 if the district floods on any of the NEXT `horizon` days
    (forecasting: today's features, tomorrow's flood - no leakage).
    Rows whose future window runs past the end of the data are dropped.
    """
    def per_district(g):
        g = g.sort_values("date").copy()
        s = g["flooded"]
        future = pd.concat([s.shift(-k) for k in range(1, horizon + 1)], axis=1)
        g["target"] = future.max(axis=1).where(future.notna().all(axis=1))
        return g

    out = pd.concat([per_district(g) for _, g in df.groupby("location_id")], ignore_index=True)
    return out.dropna(subset=["target"])


def add_target(features: pd.DataFrame, flood_days: pd.DataFrame, horizon: int = 3) -> pd.DataFrame:
    """flood_days: location_id, date (one row per flooded district-day).
    Days that are not listed are treated as "no flood"."""
    f = features.copy()
    fd = flood_days.copy()
    fd["date"] = pd.to_datetime(fd["date"])
    fd = fd.drop_duplicates(["location_id", "date"]).assign(flooded=1)
    f = f.merge(fd[["location_id", "date", "flooded"]], on=["location_id", "date"], how="left")
    f["flooded"] = f["flooded"].fillna(0)
    return target_from_flag(f, horizon)


def assemble_dataset(rain, weather, flood_labels, districts, horizon=3):
    """Full table: one row per district per day with features, flood flag and event names.

    flood_labels: district-day rows with location_id, date, event_id, confidence.
    districts: location_id, district, division.
    """
    feats = build_features(rain, weather)
    lab = flood_labels.copy()
    lab["date"] = pd.to_datetime(lab["date"])
    lab = (lab.groupby(["location_id", "date"])
              .agg(event_id=("event_id", lambda s: ";".join(sorted(set(s)))),
                   label_confidence=("confidence", lambda s: min(s, key=["low", "medium", "high"].index)))
              .reset_index())
    df = feats.merge(lab, on=["location_id", "date"], how="left")
    df["flooded"] = df["event_id"].notna().astype(int)
    df = df.merge(districts[["location_id", "district", "division"]], on="location_id", how="left")
    df[f"flood_next_{horizon}d"] = target_from_flag(df, horizon).set_index(["location_id", "date"])["target"] \
        .reindex(pd.MultiIndex.from_frame(df[["location_id", "date"]])).to_numpy()
    first = ["location_id", "district", "division", "date"]
    last = ["flooded", "event_id", "label_confidence", f"flood_next_{horizon}d"]
    mid = [c for c in df.columns if c not in first + last]
    return df[first + mid + last]


def feature_columns(df: pd.DataFrame):
    """Only genuine input features - never ids, dates, names or label columns."""
    out = []
    for c in df.columns:
        if c.startswith("rain_") or c.startswith("season_") or c == "wet_days_7d" or c in WEATHER_COLS:
            out.append(c)
    return out


def train_and_evaluate(df: pd.DataFrame, horizon: int = 3, test_fraction: float = 0.25,
                       min_train_pos: int = 30, min_test_pos: int = 10):
    """Train on the past, test on the most recent period (never random shuffling)."""
    df = df.sort_values("date")
    dates = np.sort(df["date"].unique())
    cut = dates[int(len(dates) * (1 - test_fraction))]
    gap = pd.Timedelta(days=horizon)  # keep a gap so no label window straddles the split
    train = df[df["date"] < cut - gap]
    test = df[df["date"] >= cut]

    n_tr, n_te = int(train["target"].sum()), int(test["target"].sum())
    if n_tr < min_train_pos or n_te < min_test_pos:
        raise ValueError(
            f"Not enough flood examples to train honestly: {n_tr} in the training period "
            f"and {n_te} in the test period (need at least {min_train_pos} and {min_test_pos}). "
            "Add more district flood labels (see data/flood_labels/README_district_labels.md)."
        )

    cols = feature_columns(df)
    model = HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
        l2_regularization=1.0, class_weight="balanced", random_state=0,
    )
    model.fit(train[cols], train["target"])
    score = model.predict_proba(test[cols])[:, 1]
    y = test["target"].to_numpy()

    # Simple baseline every model should beat: "heavy 3-day rain = flood"
    base = test["rain_3d"].fillna(0).to_numpy()

    top = max(1, int(len(y) * 0.05))
    order = np.argsort(-score)[:top]
    metrics = {
        "horizon_days": horizon,
        "train_rows": int(len(train)), "test_rows": int(len(test)),
        "train_flood_rows": n_tr, "test_flood_rows": n_te,
        "test_period_start": str(pd.Timestamp(cut).date()),
        "flood_rate_in_test": round(float(y.mean()), 5),
        "model_pr_auc": round(float(average_precision_score(y, score)), 4),
        "model_roc_auc": round(float(roc_auc_score(y, score)), 4),
        "baseline_rain3d_pr_auc": round(float(average_precision_score(y, base)), 4),
        "baseline_rain3d_roc_auc": round(float(roc_auc_score(y, base)), 4),
        "top5pct_precision": round(float(y[order].mean()), 4),
        "top5pct_recall": round(float(y[order].sum() / max(1, y.sum())), 4),
    }
    return model, cols, metrics


def leave_one_year_out(df: pd.DataFrame, horizon: int = 3, min_pos: int = 5):
    """Hold out one whole year at a time, train on the other years, score the held-out year.

    With only a handful of flood events, a single train/test split is very noisy;
    this shows how the model does on each flood year it has never seen.
    """
    cols = feature_columns(df)
    df = df.copy()
    years = df["date"].dt.year
    results = []
    for year in sorted(years.unique()):
        test = df[years == year]
        if test["target"].sum() < min_pos or test["target"].nunique() < 2:
            continue
        start = pd.Timestamp(year=int(year), month=1, day=1)
        train = df[(years != year) & ~((df["date"] >= start - pd.Timedelta(days=horizon)) & (df["date"] < start))]
        if train["target"].sum() < 30:
            continue
        model = HistGradientBoostingClassifier(
            max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
            l2_regularization=1.0, class_weight="balanced", random_state=0,
        ).fit(train[cols], train["target"])
        score = model.predict_proba(test[cols])[:, 1]
        y = test["target"].to_numpy()
        base = test["rain_3d"].fillna(0).to_numpy()
        results.append({
            "held_out_year": int(year), "flood_rows": int(y.sum()),
            "model_pr_auc": round(float(average_precision_score(y, score)), 4),
            "baseline_rain3d_pr_auc": round(float(average_precision_score(y, base)), 4),
            "model_roc_auc": round(float(roc_auc_score(y, score)), 4),
            "baseline_rain3d_roc_auc": round(float(roc_auc_score(y, base)), 4),
        })
    return results
