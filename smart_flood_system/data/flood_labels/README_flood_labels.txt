# Historical flood labels (2020–2025) — starter set

## Files
- `historical_flood_labels_2020_2025.csv`: one row per date for each of six existing project locations (13,149 rows). `flood_occurred=1` only for selected documented event days. Blank `flood_occurred` with `label_status=unknown_not_labeled` means UNKNOWN, not 0.
- `verified_positive_flood_days_2020_2025.csv`: only the positive days included in the starter set.
- `import_flood_labels.py`: inserts/upserts only positive rows into the project's existing SQLAlchemy `FloodEvent` model; unknown dates are skipped.

## Important limitations
This is a conservative starter set, not a complete catalogue of all floods in these cities. It does NOT claim that other dates were flood-free. Several sources describe a regional event or report a date without exact street-level coverage; review the `confidence` and `notes` columns before using labels for formal model evaluation. Tokyo currently has no positive dates in this starter set because a city-specific event/date was not sufficiently verified in the sources gathered for this file. That means Tokyo dates are unknown, not negative.
The DFO global archive contains large flood events through December 2023, but event records must be spatially checked before assigning them to a city; the source archive is here:
https://zenodo.org/records/19288171
DFO archive metadata states its information is derived from news, government, instrumental, and remote-sensing sources:
https://ckan.rimes.int/en_GB/dataset/global-active-archive-of-large-flood-events

## Source URLs used for positive labels
- Dhaka: https://www.preprints.org/manuscript/202409.0203
- Mumbai: https://www.nrsc.gov.in/nrscnew/2021_Floods.php ; https://www.ndrf.gov.in/en/pressrelease/flood-rescue-operation-ndrf-maharashtra
- Jakarta: https://jakita.jakarta.go.id/media/download/eng/edisi_1_2020.pdf
- London: https://www.gov.uk/government/publications/flood-forecasting-centre-annual-review-2021-to-2022/flood-forecasting-centre-annual-review-2021-to-2022
- New Orleans: https://www.nhc.noaa.gov/archive/2021/al09/al092021.public.015.shtml

## MySQL import
1. Copy `historical_flood_labels_2020_2025.csv` and `import_flood_labels.py` to the project root (the folder containing `backend`).
2. Check your existing location IDs in phpMyAdmin:
   `SELECT location_id, location_name FROM locations;`
3. If your IDs differ from the IDs in the CSV, edit the CSV IDs before importing.
4. Activate the venv from the inner project folder: `..\.venv\Scripts\activate`
5. Run: `python import_flood_labels.py --csv historical_flood_labels_2020_2025.csv`
6. Verify:
   `SELECT location_id, event_date, flood_occurred, source, description FROM flood_events WHERE event_date BETWEEN '2020-01-01' AND '2025-12-31' ORDER BY location_id, event_date;`

The importer assumes the `FloodEvent` model uses the fields shown in the project's remembered schema: `location_id`, `event_date`, `flood_occurred`, `severity`, `affected_area`, `source`, and `description`. If the model's class name or field definitions have changed, check `backend/models.py` first.
