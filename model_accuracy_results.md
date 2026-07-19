# Model Accuracy Summary

This file lists each major model experiment in the repository with the model name, technique used, and reported test accuracy.

| Model                               | Technique                    | Test Accuracy |
|-------------------------------------|------------------------------|---------------|
| Chili/Eggplant Model(Proposed Model)| Keras Sequential ANN         | 95.04%        |
| Original Model (Best Model)         | Keras Sequential ANN         | 88.54%        |
| Grouped - Random Forest             | Random Forest                | 39.69%        |
| Grouped - XGBoost                   | XGBoost                      | 36.94%        |
| Filtered - XGBoost                  | XGBoost                      | 15.32%        |
| Filtered - ANN                      | Keras Sequential ANN         | 14.63%        |
| Filtered - Random Forest            | Random Forest                | 13.66%        |
| Trimmed (Tuned)                     | Keras Sequential ANN (tuned) | 15.22%        |
| Standard Dataset                    | Keras Sequential ANN         | 10.25%        |
| No Categorical - XGBoost            | XGBoost                      | 10.25%        |
| Improved                            | Random Forest                | 9.50%         |
| Improved Prepared                   | Random Forest                | 9.50%         |
| Trimmed                             | Keras Sequential ANN         | 9.50%         |
| Feature Engineering - XGBoost       | XGBoost                      | 9.31%         |
| No Categorical - Random Forest      | Random Forest                | 8.63%         |
| Feature Engineering - Random Forest | Random Forest                | 8.44%         |
