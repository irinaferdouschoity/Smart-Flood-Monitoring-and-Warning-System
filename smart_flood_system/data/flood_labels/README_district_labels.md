# District flood labels

## What is here
- **`bd_flood_events.csv`** - 13 documented flood events (2017-2024) with the affected districts,
  start/end dates, a confidence level (`medium` / `low`), notes and **source URLs**.
  This is the file you edit.
- **`bd_district_flood_labels.csv`** - generated from the events file by
  `python scripts/build_flood_labels.py`: one row per flooded district-day
  (873 rows, 28 districts, 2017-03-28 to 2024-08-30).
- Older files in this folder (Dhaka / 6-city labels, methodology notes) belong to the first
  version of the project.

## Read this before trusting the labels
- The event dates and district lists were compiled from public reports (UN, Red Crescent, WHO,
  Dartmouth Flood Observatory, Copernicus, FFWC bulletins, news). **Please check the source URLs.**
  Start dates are usually well documented; **end dates and per-district timing are approximate**.
  A district is labelled "flooded" for the whole window even if the water reached it for only part of it.
- Only **major** events are listed. Every district-day that is not listed is treated as "no flood",
  so smaller or missing floods (for example 2018, 2021, 2023, the May 2022 flood) are counted as
  negatives. This lowers the apparent accuracy and can confuse the model. Add more events to fix it.
- `confidence = low` rows are weaker evidence (dates or district not clearly reported).

## How to add more floods
Add a row to `bd_flood_events.csv`:

    event_id,event_name,districts,start_date,end_date,confidence,notes,source_urls
    BDF-2021-XX,Short name,Sylhet;Sunamganj,2021-06-10,2021-06-18,medium,what the source says,https://...

Districts are separated by `;` and may use common spellings (Comilla/Cumilla, Bogra/Bogura ...).
Then run `python scripts/build_flood_labels.py` (it stops and tells you about unknown district names).

## Better label sources for later
- **FFWC** (Flood Forecasting and Warning Centre) daily bulletins - river levels vs danger levels.
- **Sentinel-1 radar flood maps** (Google Earth Engine / Copernicus EMS / UNOSAT) - flooded area
  per district and date; the most reliable way to label every district.
- **Dartmouth Flood Observatory archive** and the **Global Flood Database** - event lists and extents.

## Honest limits
Most large floods in Bangladesh are **river floods** driven by rain that fell upstream (India, Nepal,
Tibet: Ganges, Brahmaputra, Meghna) and by tides in the south. Local IMERG rainfall explains only
part of them, so compare the model with the simple rain-rule baseline that training prints.
