# Chili/Eggplant Model Performance Report

## Training Summary
- Dataset: `chili_eggplant_balanced_50150.csv`
- Total samples: `50150`
- Training samples: `35105`
- Validation samples: `7522`
- Test samples: `7523`
- Classes: `Chili, Eggplant`
- Test accuracy: `0.9504`
- ROC AUC: `0.9951`
- Average precision (micro): `0.9952`
- Average precision (macro): `0.9952`
- Best F1-score: `0.9541` at threshold `0.46`
- Best threshold accuracy: `0.9529` at threshold `0.46`

## Evaluation Artifacts
- Confusion matrix CSV: `model/chili_eggplant_model\analysis\confusion_matrix.csv`
- Confusion matrix image: `model/chili_eggplant_model\analysis\confusion_matrix.png`
- ROC curve image: `model/chili_eggplant_model\analysis\roc_curve.png`
- Precision-recall curve image: `model/chili_eggplant_model\analysis\precision_recall_curve.png`
- Precision-confidence curve image: `model/chili_eggplant_model\analysis\precision_confidence_curve.png`
- Recall-confidence curve image: `model/chili_eggplant_model\analysis\recall_confidence_curve.png`
- Average precision per class: `{'Chili': 0.9952148664694693, 'Eggplant': 0.9952043240790124}`
- F1-score curve image: `model/chili_eggplant_model\analysis\f1_score_curve.png`
- Accuracy curve image: `model/chili_eggplant_model\analysis\accuracy_curve.png`
- Threshold metrics CSV: `model/chili_eggplant_model\analysis\threshold_metrics.csv`
- Correlation matrix CSV: `model/chili_eggplant_model\analysis\correlation_matrix.csv`
- Correlation matrix image: `model/chili_eggplant_model\analysis\correlation_matrix.png`
- Accuracy/Loss plot: `model/chili_eggplant_model\analysis\accuracy_loss.png`
- Training accuracy plot: `model/chili_eggplant_model\analysis\training_accuracy.png`
- Training loss plot: `model/chili_eggplant_model\analysis\training_loss.png`

## Saved Model Files
- Final Keras model: `model/chili_eggplant_model\chili_eggplant_model.keras`
- Final H5 model: `model/chili_eggplant_model\chili_eggplant_model.h5`
- Label encoder: `model/chili_eggplant_model\label_encoder.save`
- Scaler: `model/chili_eggplant_model\scaler.save`

## Notes
- The training script keeps `model_training.py` untouched.
- Use the saved `label_encoder.save` and `scaler.save` for inference.
