# Chili/Eggplant Model Comparison

This file summarizes the comparison of the Chili/Eggplant model against other CropRotationAI experiments.

## Summary
- Dataset: `chili_eggplant_balanced_50150.csv`
- Problem type: Binary classification (`Chili` vs `Eggplant`)
- Test accuracy: `0.9504`
- ROC AUC: `0.9951`
- Average precision (micro): `0.9952`
- Average precision (macro): `0.9952`

## Comparison highlights
- This binary model is the strongest performer in the repository, thanks to the reduced class complexity.
- Compared to the original 6-crop model in `model/analysis`, the Chili/Eggplant model achieves higher raw accuracy because it only distinguishes between two classes.
- It also outperforms the 11-class experiments like `model_dataset/analysis` and `model_dataset_trimmed/analysis` by a wide margin.

## Key artifacts
- Performance report: `performance_report.md`
- Training history: `training_history.csv`
- Accuracy & loss plot: `accuracy_loss.png`
- ROC curve: `roc_curve.png`
- Precision-recall curve: `precision_recall_curve.png`
- Confusion matrix: `confusion_matrix.png`

## Notes
- Use this file as a quick reference when comparing the Chili/Eggplant experiment to broader crop classification models.
- The binary classification setting makes this model easier to optimize than the full 11-class crop prediction problem.
