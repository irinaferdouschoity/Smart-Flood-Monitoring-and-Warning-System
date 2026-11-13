# Haor flood-event dataset: baseline preparation and training report

## Dataset audit
- Input: `haor_flood_events_v1.csv`
- Rows: 77
- Columns: 18
- Date range: 2014-12-10 to 2024-10-15
- Labels: 0 = 45; 1 = 32
- Missing values: `ndwi` has 5 missing values; all other columns have no missing values.
- Duplicate full rows: 0
- Duplicate dates: 0
- Duplicate event IDs: 0

## Preparation choices
- Standardized `date` to ISO YYYY-MM-DD and `flood_label` to integer.
- Kept the original `source` column for provenance, but did not use it as a model feature because source descriptions may reveal the label.
- Excluded `event_id`, `date`, and `source` from model predictors.
- Median-imputed the 5 missing `ndwi` values inside a scikit-learn pipeline, fitted on training data only.
- Used the 14 numeric environmental/satellite features.

## Baseline model
- Algorithm: Random Forest, 300 trees, class_weight='balanced', random_state=42.
- Split: stratified random 75% train / 25% test, random_state=42.
- Train rows: 57; test rows: 20.
- Test labels: {0: 12, 1: 8}
- Accuracy: 0.850
- Balanced accuracy: 0.833
- ROC-AUC: 0.891
- Confusion matrix (rows=true [0,1], columns=predicted [0,1]): [[11, 1], [2, 6]]

### Per-class metrics
              precision    recall  f1-score   support

           0       0.85      0.92      0.88        12
           1       0.86      0.75      0.80         8

    accuracy                           0.85        20
   macro avg       0.85      0.83      0.84        20
weighted avg       0.85      0.85      0.85        20


## Critical limitations
1. Only 77 samples; a 20-row test set gives highly uncertain metrics.
2. A random split may place observations from the same flood season or related events in both train and test sets. These metrics are a quick baseline, not robust evidence of generalization.
3. Label definitions and source evidence need independent verification. A source description such as "below average flood year" does not automatically prove that a particular sample is a non-flood observation.
4. The data are from the Haor region and include SAR/satellite-specific features (VV, VH, NDWI, upstream VV, TWI, slope). The model is not automatically compatible with the six-city NASA POWER dataset, whose feature columns differ.
5. Do not use this model to claim validated real-time flood forecasting for Dhaka, Mumbai, Jakarta, London, New Orleans, or Tokyo. It is a research/demo baseline for the Haor dataset only.
