# No Categorical Features Comparison

This file summarizes the experiment that removes categorical features and compares Random Forest and XGBoost.

## Summary
- Model location: `model_dataset_no_cat/analysis`
- Experiment: dataset without categorical features
- XGBoost accuracy: `0.1025`
- Random Forest accuracy: `0.0863`

## Comparison highlights
- XGBoost performs better than Random Forest on the no-categorical-features dataset.
- The accuracy is comparable to the standard 11-class model, indicating that removing categorical features did not provide a large benefit in this case.

## Key artifacts
- XGBoost summary: `summary_xgb.json`
- Random Forest summary: `summary_rf.json`
- Classification reports: `classification_report_xgb.csv`, `classification_report_rf.csv`
- Confusion matrices: `confusion_matrix_xgb.png`, `confusion_matrix_rf.png`

## Notes
- Use this comparison file when evaluating the impact of dropping categorical inputs from the crop prediction pipeline.
