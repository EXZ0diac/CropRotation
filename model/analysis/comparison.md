# Original Model Comparison

This file summarizes the original 6-crop model's performance and compares it to the wider experiment set.

## Summary
- Model location: `model/analysis`
- Dataset: original 6-crop dataset
- Test accuracy: `0.8854`
- Classes: `Paddy`, `Maize`, `Chili`, `Cucumber`, `Groundnut`, `Spinach`

## Comparison highlights
- This model is the best performing multi-class model in the repository.
- It significantly outperforms the 11-class experiments in `model_dataset/analysis`, `model_dataset_trimmed/analysis`, and other full-crop datasets.
- It also outperforms grouped- and filtered-dataset experiments by a large margin when measured on raw accuracy.

## Key artifacts
- Performance report: `performance_report.md`
- Confusion matrix: `confusion_matrix.png`
- Correlation matrix: `correlation_matrix.png`
- Training curves: `accuracy_loss.png`

## Notes
- This comparison file is useful when contrasting the original multi-class crop model against dataset transformations, feature engineering, and simplified label strategies.
