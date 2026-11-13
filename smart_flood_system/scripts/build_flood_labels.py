"""Turn the sourced flood-event list into district flood-day labels.

    python scripts/build_flood_labels.py

Reads  data/flood_labels/bd_flood_events.csv   (one row per event: districts + start/end date)
Writes data/flood_labels/bd_district_flood_labels.csv  (one row per flooded district-day)

To teach the model more floods, add rows to bd_flood_events.csv (with a source URL) and re-run.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from district_model.names import norm

EVENTS = ROOT / "data" / "flood_labels" / "bd_flood_events.csv"
DISTRICTS = ROOT / "data" / "bangladesh_districts.csv"
OUT = ROOT / "data" / "flood_labels" / "bd_district_flood_labels.csv"


def main():
    ev = pd.read_csv(EVENTS)
    known = {norm(n): (int(i), n) for i, n in zip(*pd.read_csv(DISTRICTS)[["location_id", "district"]].T.values)}

    rows, problems = [], []
    for e in ev.itertuples():
        start, end = pd.Timestamp(e.start_date), pd.Timestamp(e.end_date)
        if end < start:
            problems.append(f"{e.event_id}: end date before start date")
            continue
        for name in str(e.districts).split(";"):
            hit = known.get(norm(name))
            if hit is None:
                problems.append(f"{e.event_id}: unknown district '{name.strip()}'")
                continue
            for day in pd.date_range(start, end):
                rows.append({"district": hit[1], "location_id": hit[0], "date": day.date(),
                             "flooded": 1, "event_id": e.event_id, "confidence": e.confidence})
    if problems:
        raise SystemExit("Fix these problems in bd_flood_events.csv:\n  " + "\n  ".join(problems))

    out = pd.DataFrame(rows).sort_values(["date", "district"])
    out.to_csv(OUT, index=False)
    print(f"{len(ev)} events -> {len(out)} flooded district-days "
          f"in {out['district'].nunique()} districts ({out['date'].min()} to {out['date'].max()})")
    print(out.groupby('confidence').size().to_string())
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
