# Standard Dataset Comparison

This file summarizes the standard 11-class dataset experiment and compares it with related dataset variants.

## Summary
- Model location: `model_dataset/analysis`
- Dataset: standard 11-crop dataset
- Test accuracy: `0.1025`
- Classes: 11 crop types

## Comparison highlights
- This baseline 11-class experiment underperforms compared to the original 6-crop model, showing how class complexity drives accuracy down.
- It performs similarly to the no-categorical-features and improved dataset experiments, with all 11-class results clustered in the 8-15% accuracy range.
- The trimmed dataset experiment improves to `15.22%` in its tuned configuration, showing the value of feature selection and tuning.

## Key artifacts
- Performance report: `performance_report.md`
- Confusion matrix: `confusion_matrix.png`
- Correlation matrix: `correlation_matrix.png`
- Training curves: `accuracy_loss.png`

## Notes
- Use this comparison file to understand how the standard 11-class dataset stacks up against alternative preprocessing and grouping strategies.
