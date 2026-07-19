# Filtered Dataset Comparison

This file summarizes the filtered dataset experiment and compares the ANN, Random Forest, and XGBoost models.

## Summary
- Model location: `model_dataset_filtered/analysis`
- Experiment: filtered crop dataset
- XGBoost accuracy: `0.1532`
- ANN accuracy: `0.1463`
- Random Forest accuracy: `0.1366`

## Comparison highlights
- XGBoost achieves the highest accuracy on this filtered dataset.
- ANN is a close second, indicating neural networks remain competitive for this experiment.
- Random Forest is slightly behind, showing that the filtered dataset has non-linear patterns that XGBoost and ANN can better leverage.

## Key artifacts
- Summaries: `summary_xgb.json`, `summary_ann.json`, `summary_rf.json`
- Classification reports: `classification_report_xgb.csv`, `classification_report_ann.csv`, `classification_report_rf.csv`
- Confusion matrices: `confusion_matrix_xgb.png`, `confusion_matrix_ann.png`, `confusion_matrix_rf.png`

## Notes
- Use this comparison file to identify the strongest model class on the filtered dataset and to measure dataset selection impact.
