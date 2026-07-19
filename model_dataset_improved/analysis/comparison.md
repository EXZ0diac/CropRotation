# Improved Dataset Comparison

This file summarizes the improved dataset experiment and compares it against related prepared datasets.

## Summary
- Model location: `model_dataset_improved/analysis`
- Experiment: improved feature/label preprocessing
- Random Forest accuracy: `0.0950`

## Comparison highlights
- This model matches the `model_dataset_improved_prepared` accuracy, suggesting the improvement step and prepared dataset are both similarly effective.
- It also compares to standard 11-class models, where the improved dataset maintains a small accuracy advantage over baseline methods.

## Key artifacts
- Summary: `summary.json`
- Classification report: `classification_report_rf.csv`
- Confusion matrix: `confusion_matrix_rf.png`
- Feature importances: `feature_importances_rf.png`
- EDA notes: `eda_summary.md`

## Notes
- Use this comparison file to track how dataset preprocessing improvements affect downstream Random Forest performance.
