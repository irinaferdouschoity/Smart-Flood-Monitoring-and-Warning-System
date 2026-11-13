import sys,pandas as pd
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.database import SessionLocal
from backend.models import FloodEvent,Location
if len(sys.argv)!=2: raise SystemExit('Usage: python scripts/import_flood_events.py path/to/real.csv')
df=pd.read_csv(sys.argv[1]); required={'location_id','event_date','flood_occurred'}; missing=required-set(df.columns)
if missing: raise SystemExit(f'Missing columns: {sorted(missing)}')
db=SessionLocal()
try:
    for r in df.to_dict('records'):
        if not db.get(Location,int(r['location_id'])): continue
        db.add(FloodEvent(location_id=int(r['location_id']),event_date=pd.to_datetime(r['event_date']).date(),flood_occurred=bool(int(r['flood_occurred'])),severity=r.get('severity'),affected_area=(float(r['affected_area']) if pd.notna(r.get('affected_area')) else None),source=r.get('source'),description=r.get('description'),created_at=pd.Timestamp.utcnow().to_pydatetime()))
    db.commit(); print('Import completed.')
except Exception as e: db.rollback(); raise SystemExit(str(e))
finally: db.close()
