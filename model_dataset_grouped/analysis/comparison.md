# Grouped Dataset Comparison

This file summarizes the grouped dataset experiment and compares Random Forest and XGBoost results.

## Summary
- Model location: `model_dataset_grouped/analysis`
- Experiment: grouping multiple crops into broader categories
- Random Forest accuracy: `0.3969`
- XGBoost accuracy: `0.3694`

## Comparison highlights
- Grouping crops into fewer categories leads to much higher accuracy than the full 11-class problem.
- Random Forest performs slightly better than XGBoost for this grouped classification task.
- This experiment demonstrates how label simplification can improve model performance when fine-grained crop classes are too similar.

## Key artifacts
- Grouping summary: `grouping_summary.txt`
- Confusion matrix: `confusion_matrix_grouped.png`
- Feature importances: `feature_importances_grouped.png`

## Notes
- Use this comparison file when deciding whether to simplify labels for better predictive performance.
