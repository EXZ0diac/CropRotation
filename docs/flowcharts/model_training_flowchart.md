# Flowchart for `model_training.py`

Mermaid diagram describing data generation, training, evaluation, and analysis artifact creation.

```mermaid
flowchart TD
  Start([Start training script])
  Start --> SetSeed["Set deterministic seeds (numpy, random, tf)"]
  SetSeed --> DefineCrops["Define crops and soil midpoints"]
  DefineCrops --> GenerateData["Generate augmented samples around midpoints (noise)"]
  GenerateData --> BuildXy["Build X (features) and y (labels) arrays"]
  BuildXy --> Scale["Fit MinMaxScaler and transform features"]
  Scale --> Encode["Label-encode targets and to_categorical()"]
  Encode --> Split["Train/Val/Test split (stratified)"]
  Split --> BuildModel["Build Sequential ANN and compile (loss, metrics)"]
  BuildModel --> Train["model.fit(...) with EarlyStopping and ModelCheckpoint"]
  Train --> SaveModel["Save model (.keras, optionally .h5) and preprocessors"]
  SaveModel --> Evaluate["Predict on X_test, compute accuracy & classification report"]
  Evaluate --> Analysis["Compute & save: correlation matrix, confusion matrix, classification_report CSV, accuracy/loss plots"]
  Analysis --> End([Done — artifacts in model/analysis/])
```

Notes:
- Training history (`history.history`) is used to plot Accuracy vs Epoch and Loss vs Epoch.
- Analysis artifacts are written to `model/analysis/`:
  - `correlation_matrix.csv` / `.png`
  - `confusion_matrix.csv` / `.png`
  - `classification_report.csv`
  - `accuracy_loss.png`
  - `performance_report.md`
