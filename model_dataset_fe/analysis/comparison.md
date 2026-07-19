# Feature Engineering Comparison

This file summarizes the feature engineering experiment and compares RF vs XGBoost results.

## Summary
- Model location: `model_dataset_fe/analysis`
- Experiment: feature engineering for 11-class crop prediction
- XGBoost accuracy: `0.0931`
- Random Forest accuracy: `0.0844`

## Comparison highlights
- XGBoost outperforms Random Forest on the engineered feature dataset.
- Both algorithms remain in the low-accuracy range for the 11-class problem, indicating that class complexity is still the dominant challenge.
- This experiment is useful for understanding whether feature engineering provides a modest gain over the standard dataset.

## Key artifacts
- XGBoost summary: `summary_xgb.json`
- Random Forest summary: `summary_rf.json`
- Classification reports: `classification_report_xgb.csv`, `classification_report_rf.csv`
- Confusion matrices: `confusion_matrix_xgb_fe.png`, `confusion_matrix_rf_fe.png`

## Notes
- Use this comparison file when evaluating whether engineered features meaningfully improve crop classification performance.
