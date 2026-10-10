from pathlib import Path
from datetime import datetime
import joblib,pandas as pd
MODEL_PATH=Path('models/flood_model.joblib')
def risk_level(p): return 'LOW' if p<.25 else 'MODERATE' if p<.50 else 'HIGH' if p<.75 else 'EXTREME'
def predict_from_features(features):
    if not MODEL_PATH.exists(): raise FileNotFoundError('No trained model exists. Import real flood labels and run: python -m backend.ml.train')
    b=joblib.load(MODEL_PATH); p=float(b['model'].predict_proba(pd.DataFrame([features],columns=b['feature_columns']))[0,1]); return {'prediction_time':datetime.utcnow(),'flood_probability':p,'risk_level':risk_level(p),'model_version':b['model_version']}
