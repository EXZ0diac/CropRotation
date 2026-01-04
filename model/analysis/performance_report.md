# Model Performance Report

**Test accuracy:** 0.8854

## Classification report

**Note:** Optional dependency 'tabulate' is not installed. Install with `pip install tabulate` to get a prettier markdown table.

              precision    recall  f1-score       support
Paddy          0.885748  0.890356  0.888046   2499.000000
Maize          0.870275  0.874101  0.872183   2502.000000
Chili          0.897249  0.887910  0.892555   2498.000000
Cucumber       0.870296  0.874497  0.872392   2486.000000
Groundnut      0.897291  0.890092  0.893677   2493.000000
Spinach        0.891828  0.895363  0.893592   2523.000000
accuracy       0.885408  0.885408  0.885408      0.885408
macro avg      0.885448  0.885387  0.885408  15001.000000
weighted avg   0.885463  0.885408  0.885426  15001.000000

## Artifacts

- Correlation matrix CSV: `correlation_matrix.csv`
- Correlation matrix image: `correlation_matrix.png`
- Confusion matrix CSV: `confusion_matrix.csv`
- Confusion matrix image: `confusion_matrix.png`
- Classification report CSV: `classification_report.csv`
- Training curves image: `accuracy_loss.png`
