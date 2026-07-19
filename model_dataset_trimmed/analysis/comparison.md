# Trimmed Dataset Comparison

This file summarizes the trimmed dataset experiment and compares the tuned ANN with the standard trimmed configuration.

## Summary
- Model location: `model_dataset_trimmed/analysis`
- Experiment: trimmed dataset for 11-class crop prediction
- Tuned ANN accuracy: `0.1522`
- Standard ANN accuracy: `0.0950`

## Comparison highlights
- Hyperparameter tuning provides a notable accuracy boost over the standard trimmed configuration.
- The trimmed dataset is more effective than the raw 11-class baseline, but still far from the easier grouped and binary classification tasks.

## Key artifacts
- Tune summary: `ann_tune_summary.json`
- Best model: `ann_tuned_model.keras`
- Classification report: `classification_report_ann_trimmed.csv`
- Confusion matrix: `confusion_matrix_ann_trimmed.png`
- Tuning results: `ann_tune_results.csv`

## Notes
- Use this comparison file when reviewing the value of search-based tuning for the trimmed dataset.
