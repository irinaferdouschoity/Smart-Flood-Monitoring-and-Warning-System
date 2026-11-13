# data/ folder

## Already included (small, needed)
- `city_specific_risk.csv` - daily weather 2020-2026 for the 6 cities + rainfall thresholds.
  **Required** by the app (rainfall indicator) and used by `scripts/import_weather_csv.py`.
- `flood_labels/` - verified flood-day labels and notes. Used by `scripts/import_flood_labels.py`.
  `flood_events.csv.example` is only a blank template - don't import it as-is.

## Where to put your big data (the ~1 GB you didn't upload)
- **`imerg_downloads/`** - put your NASA IMERG `.nc4` / `.HDF5` satellite files here.
  `scripts/download_imerg_batch.py` also saves new downloads into this folder.
  The dashboard does **not** read these files; they are only used to fill the
  `satellite_precipitation` table. You can leave this folder empty and the app still runs.

If you have other raw data (extra CSVs, test files such as `imerg_test`), keep them in
`data/` too, but nothing outside the files listed above is required.
