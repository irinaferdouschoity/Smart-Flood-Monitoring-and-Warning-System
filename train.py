from pathlib import Path
from datetime import datetime
import joblib,pandas as pd
from sqlalchemy import select
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score,precision_score,recall_score,f1_score,roc_auc_score,confusion_matrix
from ..database import SessionLocal
from ..models import Location,WeatherObservation,FloodEvent,ModelRun
from .features import FEATURE_COLUMNS,build_training_dataset
MODEL_PATH=Path('models/flood_model.joblib'); VERSION='random_forest_v1'
def main():
    db=SessionLocal()
    try:
        locs={x.location_id:(float(x.latitude),float(x.longitude)) for x in db.scalars(select(Location)).all()}; ws=db.scalars(select(WeatherObservation).order_by(WeatherObservation.location_id,WeatherObservation.observation_date)).all(); fs=db.scalars(select(FloodEvent)).all()
        if not ws: raise SystemExit('Training stopped: no weather observations exist.')
        if not fs: raise SystemExit('Training stopped: no real historical flood labels exist.')
        weather=pd.DataFrame([{'location_id':x.location_id,'observation_date':x.observation_date,'precipitation':x.precipitation,'temperature_avg':x.temperature_avg,'temperature_max':x.temperature_max,'temperature_min':x.temperature_min,'humidity':x.humidity,'dew_point':x.dew_point,'wind_speed':x.wind_speed,'surface_pressure':x.surface_pressure,'latitude':locs[x.location_id][0],'longitude':locs[x.location_id][1]} for x in ws]); floods=pd.DataFrame([{'location_id':x.location_id,'event_date':x.event_date,'flood_occurred':int(x.flood_occurred)} for x in fs]); d=build_training_dataset(weather,floods); counts=d.flood_occurred.value_counts()
        if set(counts.index)!={0,1} or counts.min()<20: raise SystemExit(f'Training stopped: need both real classes with at least 20 rows each. Counts: {counts.to_dict()}')
        d=d.sort_values('observation_date'); split=int(len(d)*.8); tr,te=d.iloc[:split],d.iloc[split:]
        if te.flood_occurred.nunique()<2: raise SystemExit('Training stopped: chronological test set contains only one class. Add more real historical data.')
        m=RandomForestClassifier(n_estimators=300,random_state=42,class_weight='balanced',min_samples_leaf=2,n_jobs=-1); m.fit(tr[FEATURE_COLUMNS],tr.flood_occurred); prob=m.predict_proba(te[FEATURE_COLUMNS])[:,1]; pred=(prob>=.5).astype(int); metrics={'accuracy':accuracy_score(te.flood_occurred,pred),'precision':precision_score(te.flood_occurred,pred,zero_division=0),'recall':recall_score(te.flood_occurred,pred,zero_division=0),'f1':f1_score(te.flood_occurred,pred,zero_division=0),'roc_auc':roc_auc_score(te.flood_occurred,prob)}; print(confusion_matrix(te.flood_occurred,pred)); print(metrics); MODEL_PATH.parent.mkdir(exist_ok=True); joblib.dump({'model':m,'feature_columns':FEATURE_COLUMNS,'model_version':VERSION,'trained_at':datetime.utcnow().isoformat()},MODEL_PATH); db.add(ModelRun(model_name=VERSION,training_date=datetime.utcnow(),dataset_size=len(d),accuracy=metrics['accuracy'],precision_score=metrics['precision'],recall_score=metrics['recall'],f1_score=metrics['f1'],roc_auc=metrics['roc_auc'],model_file=str(MODEL_PATH),notes='Chronological 80/20 holdout using real database labels.')); db.commit(); print(f'Saved {MODEL_PATH}')
    finally: db.close()
if __name__=='__main__': main()
