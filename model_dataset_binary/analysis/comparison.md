# Binary Dataset Comparison

This file summarizes the binary dataset analysis for CropRotationAI.

## Summary
- Model location: `model_dataset_binary/analysis`
- Dataset type: binary crop classification
- Available models: Random Forest, XGBoost

## Comparison highlights
- This analysis compares the binary classifiers against each other using confusion matrices and feature importances.
- Binary classification typically performs better than high-class-count problems, but may still depend on the label grouping strategy.
- Use this folder to review how well the binary modeling approach matches the original crop categories.

## Key artifacts
- Confusion matrix: `confusion_binary.png`
- Feature importances: `feature_importances_binary.png`
- Summary CSV: `feature_importances_binary.csv`

## Notes
- If available, add numeric accuracy or F1 metrics to the binary experiment report to complete the comparison.
