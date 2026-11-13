# Flood-label dataset methodology and audit trail

Generated: 2026-10-10. Label window: 2020-01-01 through 2026-10-05 inclusive.

## Scope and status

The supplied candidate file contained 11 records across Tokyo, New Orleans, Mumbai, Jakarta, Dhaka, and London. The audit reviewed all 11 candidate rows. This is a conservative, partial audit—not an exhaustive census of every flood during the period. The daily file is a complete date/location grid, but it is **not** a complete observed flood/no-flood record.

No NASA POWER weather or NASA GPM IMERG data were downloaded or re-downloaded. The MySQL database was not available to this run, so the join was not executed.

## Source and verification policy

Candidate sources were treated as leads, not truth. Where possible, original source pages were opened and inspected rather than relying on search snippets.

- Westminster City Council, “July 2021 flooding” (https://www.westminster.gov.uk/residents/floods/july-2021-flooding): opened and inspected. It explicitly identifies major flood events on 12 and 25 July 2021 and describes flooding in parts of Westminster. These are retained as Grade A locality-level events. The evidence supports flooding in the named borough, not inundation at every point in London or at the exact weather station/reference coordinate.
- Tokyo Metropolitan Government, “Tokyo Metropolitan Government Disaster Prevention Guide Book” page 64 (https://www.bousai.metro.tokyo.lg.jp/content/e_book_2025/2025-12_GDP_GuideBook_en/pageindices/index64.html): opened and inspected. It lists Tokyo wind/flood damage events on 8–11 October 2020, 8 August 2021, and 30 September–1 October 2021. The inspected page does not provide a sufficiently clear ward-level footprint or flood polygon for the requested 20 km spatial rule. These events are Grade B and review-only, not strict positives.
- National Weather Service New Orleans Hurricane Zeta post-tropical cyclone report (https://www.weather.gov/lch/2020Zeta-PSHLIX): opened and inspected. Orleans Parish is listed in the report, but the report states no significant inland flooding was reported or expected and discusses surge flooding at other locations. This does not support a positive label at the target location.
- The official Jakarta BPBD annual-report landing page (https://bpbd.jakarta.go.id/index.php/ppid/regulasi/5/laporan-tahunan) was found and inspected via its search-indexed content; individual annual report documents were not extracted for dated events.
- The Mumbai archival report URL, Bangladesh-wide Global Flood Records URL, and the general NOAA storm-surge archive were present in the candidate file but were not independently inspected to event-level evidence in this run. Their claims remain unverified.

The audit CSV records the result and reason for each candidate. No additional event has been promoted to Grade A without evidence that meets the stated rules.

## Spatial matching

The supplied coordinates are treated as reference points, not the complete geographic extent of each metropolis. A proposed default spatial rule is: an authoritative flood polygon intersects a 20 km geodesic buffer around the reference point, or an official source explicitly documents flooding in the named target city/borough. A match establishes locality relevance only; it does not prove that the exact coordinate or every part of the city was inundated.

For the London rows, the source explicitly documents flooding in parts of Westminster, a borough within London and close to the supplied London reference point. The event records use an approximate Westminster coordinate only as a locality marker; it is not an extracted flood coordinate. Tokyo's source is metropolitan-level and lacks a usable ward/polygon match in the inspected text, so it remains Grade B. Regional, country-wide, storm-track, and warning-only evidence is insufficient.

## Temporal rules and daily labels

- Positive (`1`): only dates with Grade A local flood evidence are marked positive in the strict daily file.
- Negative (`0`): no dates are marked negative in this release. No systematic, adequate daily observation/coverage source was established to support a defensible claim of no qualifying flood.
- Unknown (`NULL`/blank): all dates not supported by a Grade A event remain unknown. An absent report is not evidence of no flood.
- The London events are two separate dates, 12 July and 25 July 2021. Dates between them are not expanded as positive.
- Tokyo event date ranges are preserved in the event table as Grade B review records. They are not expanded into strict daily positives. If later used for exploratory labels, range-expanded dates must be flagged as inferred, not daily direct observations.
- Daily CSV has one row for each of the six location IDs and each of the 2,470 dates from 2020-01-01 through 2026-10-05 (14,820 rows total).

## Satellite data and weather features

This release does not use NASA POWER or GPM IMERG rainfall to establish flood occurrence. Rainfall is a predictor, not ground truth. Satellite-derived flood maps can miss events because of revisit time, cloud/vegetation effects, urban built-up areas, spatial resolution, observation gaps, and product-specific detection thresholds. A non-detection must not be translated into a negative label without a documented observation model and adequate coverage.

## Reproducibility and database join

1. Keep `verified_flood_events.csv`, `daily_flood_labels_2020_2026.csv`, and `flood_event_source_audit.csv` as separate event, daily-label, and audit tables.
2. Use `match_existing_weather.py` against the existing MySQL database. It creates only a connection-scoped temporary label table and performs a SELECT join; it does not download or update NASA observations.
3. The script assumes `weather_observations` has `location_id` and `observation_date` columns. Confirm the actual date column type/name before running. Set connection details using `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` environment variables.
4. Validate unique `(location_id, observation_date)` labels, event IDs, date range, and location IDs after every revision.

## Machine-learning safeguards

There are only two strict positive daily labels in this release and zero defensible negative labels. This is not sufficient for a supervised flood classifier, and metrics such as accuracy, precision, recall, F1, or ROC-AUC must not be reported from this dataset. Unknown labels must be excluded from ordinary binary training, not coerced to zero. Any future split should be chronological and grouped by event, with all dates from one event kept in a single partition. Avoid randomly splitting adjacent days from the same event across train and test.

For a final-year demonstration, either collect systematic flood/no-flood observation coverage (including authoritative river/street gauge or flood-map evidence) or present a transparent rule-based monitoring prototype without claiming validated predictive performance.
