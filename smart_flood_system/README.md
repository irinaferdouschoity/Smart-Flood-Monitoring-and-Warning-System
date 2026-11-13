# Smart Flood Monitoring and Warning System

A FastAPI + MySQL web dashboard that shows weather, rainfall indicators, flood history
and an experimental ML flood-risk estimate for six cities (Dhaka, Mumbai, Jakarta,
London, New Orleans, Tokyo).

> The prediction uses a model trained on **Haor (Bangladesh) data only** and has not been
> validated for these cities. It is a research demo, **not** an operational flood warning.

> **New to this? Follow `HOW_TO_RUN.md` - a detailed step-by-step guide.**

## Quick start (Windows)

1. Install **Python 3.14** (what this project was built with; 3.12/3.13 should also work)
   from python.org and tick **"Add Python to PATH"**.
2. Install **XAMPP**, open the XAMPP Control Panel and **Start MySQL**.
3. Double-click **`setup.bat`** (first time only). It creates the virtual environment,
   installs packages, creates the database + tables, and loads the saved weather and
   flood-history data.
4. Double-click **`run.bat`**. The dashboard opens at <http://127.0.0.1:8000/>
   (API docs: <http://127.0.0.1:8000/docs>). Keep the black window open while using it.

If your MySQL root user has a password, edit `.env` before step 3:
`DATABASE_URL=mysql+pymysql://root:YOURPASSWORD@localhost:3306/smart_flood_system`

## Automatic NASA download

While the app is running it downloads NASA POWER weather into MySQL by itself:
once a few seconds after start-up, then every 6 hours. It only fetches missing days
(plus the last 7 days, which NASA corrects late) and never creates duplicates.
On an empty database the first run downloads 2020 -> yesterday for every city, which can take a
minute or two. You can also press the dashboard's update button, call `POST /sync-nasa`,
or run `python scripts/sync_nasa_data.py`.

Settings in `.env`: `AUTO_SYNC_NASA=false` turns the background job off,
`AUTO_SYNC_HOURS=6` changes how often it runs. Needs an internet connection.

## Manual commands (instead of the .bat files)

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/setup_database.py
python scripts/import_weather_csv.py
python scripts/import_flood_labels.py
python -m uvicorn backend.main:app --reload
```

Note the app path is `backend.main:app` (not `main:app`).

## Folder layout

| Path | Purpose |
|---|---|
| `backend/` | FastAPI app, database models, NASA fetchers, ML prediction code |
| `frontend/` | Dashboard (HTML / CSS / JS) |
| `haor_model/` | Trained model (`haor_flood_model.joblib`) + training script and cleaned dataset |
| `sql/schema.sql` | Database tables |
| `scripts/` | Setup and data-loading helpers (see below) |
| `data/` | Data files - see `data/README.md` |
| `.env` | Your local settings (never upload to GitHub) |

## Scripts

| Script | What it does |
|---|---|
| `setup_database.py` | Creates the database, tables and 6 starter locations |
| `import_weather_csv.py` | Loads 2020-2026 daily weather from `data/city_specific_risk.csv` (offline) |
| `import_flood_labels.py` | Loads verified flood days from `data/flood_labels/` (used by "Flood History") |
| `sync_nasa_data.py` | Downloads all missing NASA weather days straight into MySQL (only fetches what's new) |
| `update_nasa_data.py` | Downloads fresh NASA POWER weather (internet needed). Example: `python scripts/update_nasa_data.py --start 2026-10-01 --end 2026-11-05` |
| `update_imerg_data.py`, `download_imerg_batch.py`, `save_imerg_to_mysql.py` | Optional NASA IMERG satellite rainfall. Needs `pip install -r requirements-optional.txt` and an Earthdata login. The dashboard does not need these. |
| `import_flood_events.py` | Imports your own flood-event CSV (template: `data/flood_labels/flood_events.csv.example`) |

## Bangladesh 64-district rainfall + ML

| Step | Command | What it does |
|---|---|---|
| 1 | `python scripts/setup_bd_districts.py` | adds the 64 districts to MySQL |
| 2 | `python scripts/sync_imerg_districts.py` | downloads daily IMERG rainfall (2015 -> now, resumable, no login, ~30-60 min) |
| 3 | `python scripts/build_flood_labels.py` | turns `data/flood_labels/bd_flood_events.csv` into flood-day labels |
| 4 | `python district_model/build_dataset.py` | creates **`data/bd_district_training_dataset.csv`** (rain + weather + flood days) |
| 5 | `python district_model/train_district_model.py` | trains the model and prints honest checks |

Read `data/flood_labels/README_district_labels.md`: the flood labels come from 13 documented
major events and are approximate. Add more events to the events file to improve the model.
The auto-sync also keeps the 64 districts' NASA POWER weather up to date once they are added.

## Troubleshooting

- **"Could not connect to MySQL"** - MySQL is not started in XAMPP, or the password in `.env` is wrong.
- **Empty dropdown** - run `python scripts/setup_database.py`.
- **No graphs / "No weather observations"** - run `python scripts/import_weather_csv.py`, or press the dashboard's update button (needs internet).
- **PowerShell blocks activation** - run `Set-ExecutionPolicy -Scope Process RemoteSigned`, then activate again.
- **Port 8000 already in use** - add `--port 8001` to the uvicorn command.

## Credits

Haor flood dataset: Koli & Jely, *A SAR-verified flash flood event dataset for the haor
wetlands of northeastern Bangladesh (2014-2024)*, CC BY 4.0. The version here was cleaned for ML
experiments; source, date and event_id columns were excluded from predictors to reduce leakage.
Weather: NASA POWER.
