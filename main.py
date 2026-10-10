
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Any
import csv
import math

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from .database import get_db
from .models import (
    Location,
    WeatherObservation,
    FloodEvent,
    FloodPrediction,
    SatellitePrecipitation,
)
from .schemas import (
    LocationCreate,
    LocationOut,
    WeatherOut,
    FloodEventOut,
    PredictionOut,
    PredictionRequest,
)
from .services.data_service import upsert_power_data, latest_features
from .ml.predict import predict_from_features
from .ml.haor_predict import predict_haor
from .nasa.imerg import fetch_nearest_precipitation


app = FastAPI(
    title="Smart Flood Monitoring and Warning System",
    version="1.2.0",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONT = PROJECT_ROOT / "frontend"
RAINFALL_CSV = PROJECT_ROOT / "city_specific_risk.csv"


class HaorPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: dict[str, Any]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(FRONT / "index.html")


@app.get("/static/{name}", include_in_schema=False)
def static(name: str):
    if name not in {"app.js", "style.css"}:
        raise HTTPException(404, "Not found")
    return FileResponse(FRONT / name)


@app.get("/locations", response_model=list[LocationOut])
def locations(db: Session = Depends(get_db)):
    return db.scalars(
        select(Location).order_by(Location.location_name)
    ).all()


@app.post("/locations", response_model=LocationOut)
def add_location(p: LocationCreate, db: Session = Depends(get_db)):
    x = Location(**p.model_dump(), created_at=datetime.utcnow())
    db.add(x)
    try:
        db.commit()
        db.refresh(x)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            409, "Location already exists or is invalid."
        ) from exc
    return x


@app.get("/weather/{location_id}", response_model=list[WeatherOut])
def weather(
    location_id: int,
    limit: int = 90,
    db: Session = Depends(get_db),
):
    if not db.get(Location, location_id):
        raise HTTPException(404, "Location not found")

    rows = db.scalars(
        select(WeatherObservation)
        .where(WeatherObservation.location_id == location_id)
        .order_by(desc(WeatherObservation.observation_date))
        .limit(min(max(limit, 1), 365))
    ).all()

    return list(reversed(rows))


@app.get("/precipitation/{location_id}")
def precipitation(
    location_id: int,
    limit: int = 90,
    db: Session = Depends(get_db),
):
    rows = weather(location_id, limit, db)
    return [
        {
            "date": row.observation_date,
            "precipitation": row.precipitation,
        }
        for row in rows
    ]


@app.get(
    "/flood-history/{location_id}",
    response_model=list[FloodEventOut],
)
def history(location_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(FloodEvent)
        .where(FloodEvent.location_id == location_id)
        .order_by(desc(FloodEvent.event_date))
        .limit(500)
    ).all()
    return list(reversed(rows))


@app.get(
    "/predictions/{location_id}",
    response_model=list[PredictionOut],
)
def predictions(location_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(FloodPrediction)
        .where(FloodPrediction.location_id == location_id)
        .order_by(desc(FloodPrediction.prediction_time))
        .limit(100)
    ).all()
    return list(reversed(rows))


@app.post("/predict", response_model=PredictionOut)
def predict(p: PredictionRequest, db: Session = Depends(get_db)):
    """Original city model endpoint; kept for compatibility."""
    if not db.get(Location, p.location_id):
        raise HTTPException(404, "Location not found")

    try:
        result = predict_from_features(
            latest_features(db, p.location_id)
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc

    row = FloodPrediction(
        location_id=p.location_id,
        **result,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.post("/haor-predict")
def haor_predict_endpoint(request: HaorPredictionRequest):
    """Run the Haor model with explicitly supplied features."""
    try:
        return predict_haor(request.features)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/city-haor-predict")
def city_haor_predict(
    location_id: int,
    db: Session = Depends(get_db),
):
    """
    Experimental city estimate using available weather data.
    Unavailable satellite and terrain features are passed as NaN so
    the trained model pipeline can apply its fitted imputer.
    """
    location = db.get(Location, location_id)
    if not location:
        raise HTTPException(
            status_code=404,
            detail="Location not found.",
        )

    records = weather(location_id, limit=90, db=db)
    if not records:
        raise HTTPException(
            status_code=409,
            detail="No weather observations available. Update NASA data first.",
        )

    # weather() returns records oldest to newest.
    latest = records[-1]

    latest_date = latest.observation_date
    recent = [
        row for row in records
        if 0 <= (latest_date - row.observation_date).days < 4
    ]

    # Do not silently treat missing rainfall as zero.
    if latest.precipitation is None:
        raise HTTPException(
            status_code=409,
            detail="Latest observation has no rainfall value.",
        )

    rainfall = float(latest.precipitation)

    # Use the sum of available observations from the last four calendar days.
    # This may be incomplete if the weather data has gaps.
    rain_96h = sum(
        float(row.precipitation)
        for row in recent
        if row.precipitation is not None
    )

    temperatures = [
        float(row.temperature_avg)
        for row in records[-30:]
        if row.temperature_avg is not None
    ]

    baseline_temp = (
        sum(temperatures) / len(temperatures)
        if temperatures else None
    )

    current_temp = (
        float(latest.temperature_avg)
        if latest.temperature_avg is not None
        else None
    )

    unavailable = float("nan")

    features = {
        "VV": unavailable,
        "VH": unavailable,
        "vv_vh_ratio": unavailable,
        "rainfall": rainfall,
        "soil_moisture": unavailable,
        "temp": (
            current_temp
            if current_temp is not None
            else unavailable
        ),
        "wind": (
            float(latest.wind_speed)
            if latest.wind_speed is not None
            else unavailable
        ),
        "slope": unavailable,
        "twi": unavailable,
        "rain_24h": rainfall,
        "ndwi": unavailable,
        "upstream_vv": unavailable,
        "rain_96h": rain_96h,
        "temp_anomaly": (
            current_temp - baseline_temp
            if current_temp is not None and baseline_temp is not None
            else unavailable
        ),
    }

    try:
        result = predict_haor(features)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    result["city"] = location.location_name
    result["weather_observation_date"] = str(latest_date)
    result["missing_live_features"] = [
        "VV",
        "VH",
        "vv_vh_ratio",
        "soil_moisture",
        "slope",
        "twi",
        "ndwi",
        "upstream_vv",
    ]
    result["warning"] = (
        "Experimental research estimate only. This model was trained on "
        "Haor data and has not been validated for this city. Satellite and "
        "terrain features were unavailable and imputed by the trained "
        "model pipeline. Do not use this result for real-world flood warnings."
    )

    return result


@app.get("/rainfall-indicator/{location_id}")
def rainfall_indicator(location_id: int):
    """Return the latest historical rainfall indicator for a known location."""
    if not RAINFALL_CSV.exists():
        raise HTTPException(
            status_code=404,
            detail="Rainfall indicator data file not found.",
        )

    try:
        latest_row = None
        with RAINFALL_CSV.open(
            "r", newline="", encoding="utf-8-sig"
        ) as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get("location_id", "").strip() == str(location_id):
                    if (
                        latest_row is None
                        or row.get("observation_date", "")
                        > latest_row.get("observation_date", "")
                    ):
                        latest_row = row
    except (OSError, csv.Error) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read rainfall indicator data.",
        ) from exc

    if latest_row is None:
        raise HTTPException(
            status_code=404,
            detail="No rainfall indicator data found for this location.",
        )

    try:
        rainfall = float(latest_row["rainfall_3day_total"])
        threshold_95 = float(latest_row["threshold_95"])
        threshold_99 = float(latest_row["threshold_99"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Rainfall indicator data has missing or "
                "invalid numeric fields."
            ),
        ) from exc

    return {
        "location_id": location_id,
        "city": latest_row.get("city", "Unknown"),
        "observation_date": latest_row.get("observation_date"),
        "rainfall_3day_total": rainfall,
        "threshold_95": threshold_95,
        "threshold_99": threshold_99,
        "rainfall_indicator": latest_row.get("rainfall_indicator"),
        "note": (
            "This is a historical rainfall indicator, not a verified "
            "flood prediction."
        ),
    }


@app.post("/update-imerg")
def update_imerg(db: Session = Depends(get_db)):
    end = datetime.utcnow()
    start = end - timedelta(hours=6)
    out = []

    for loc in db.scalars(select(Location)).all():
        try:
            rows = fetch_nearest_precipitation(
                float(loc.latitude),
                float(loc.longitude),
                start,
                end,
            )

            for row in rows:
                observed_at = row.get("observation_time")
                if isinstance(observed_at, str):
                    observed_at = datetime.fromisoformat(
                        observed_at.replace("Z", "+00:00")
                    ).replace(tzinfo=None)

                db.add(
                    SatellitePrecipitation(
                        location_id=loc.location_id,
                        observation_time=observed_at,
                        precipitation=row["precipitation"],
                        latitude=row["latitude"],
                        longitude=row["longitude"],
                        dataset=row["dataset"],
                        data_source=row["data_source"],
                        created_at=datetime.utcnow(),
                    )
                )

            db.commit()
            out.append(
                {
                    "location_id": loc.location_id,
                    "status": "success",
                    "records": len(rows),
                }
            )
        except Exception as exc:
            db.rollback()
            out.append(
                {
                    "location_id": loc.location_id,
                    "status": "error",
                    "error": str(exc),
                }
            )

    return {"start": start, "end": end, "results": out}


@app.post("/update-data")
def update(db: Session = Depends(get_db)):
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=30)
    out = []

    for loc in db.scalars(select(Location)).all():
        try:
            count = upsert_power_data(db, loc, start, end)
            out.append(
                {
                    "location_id": loc.location_id,
                    "status": "success",
                    "records": count,
                }
            )
        except Exception as exc:
            db.rollback()
            out.append(
                {
                    "location_id": loc.location_id,
                    "status": "error",
                    "error": str(exc),
                }
            )

    return {"start": start, "end": end, "results": out}
