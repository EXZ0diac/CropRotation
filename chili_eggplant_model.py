# ===============================================
#  Crop Rotation AI - Chili/Eggplant ANN Trainer
#  Separate training script based on model_training.py
#
# Usage:
#   python chili_eggplant_model.py
#
# Outputs:
#   - model/chili_eggplant_model/chili_eggplant_model.keras
#   - model/chili_eggplant_model/chili_eggplant_model.h5
#   - model/chili_eggplant_model/scaler.save
#   - model/chili_eggplant_model/label_encoder.save
#   - model/chili_eggplant_model/analysis/*
# ===============================================

import os
import json
import random

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf  # type: ignore
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint  # type: ignore
from tensorflow.keras.layers import Dense, Dropout  # type: ignore
from tensorflow.keras.models import Sequential  # type: ignore
from tensorflow.keras.optimizers import Adam  # type: ignore
from tensorflow.keras.utils import to_categorical  # type: ignore

# =====================================================
# CONFIGURATION
# =====================================================
SEED = 42
DATA_PATH = "chili_eggplant_balanced_50150.csv"
OUT_DIR = "model/chili_eggplant_model"
ANALYSIS_DIR = os.path.join(OUT_DIR, "analysis")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

np.random.seed(SEED)
random.seed(SEED)
tf.random.set_seed(SEED)

# The dataset is already balanced and contains two classes.
CLASSES = ["Chili", "Eggplant"]
FEATURE_NAMES = ["Nitrogen", "Phosphorus", "Potassium", "pH", "Humidity", "Temperature"]

# =====================================================
# LOAD DATA
# =====================================================
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

print(f"Loading dataset from {DATA_PATH}...")
df = pd.read_csv(DATA_PATH)
print("Columns:", df.columns.tolist())

required = FEATURE_NAMES + ["Crop"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise RuntimeError(f"Missing required columns: {missing}")

X = df[FEATURE_NAMES].copy().astype(float)
y = df["Crop"].astype(str).str.strip().copy()

# Normalize labels to expected casing.
y = y.replace({"chili": "Chili", "eggplant": "Eggplant"})

unknown_labels = sorted(set(y.unique()) - set(CLASSES))
if unknown_labels:
    raise RuntimeError(f"Unexpected crop labels in dataset: {unknown_labels}")

print("Class counts:\n", y.value_counts().to_string())

# Correlation matrix for the raw features.
corr_df = X.corr()
corr_csv = os.path.join(ANALYSIS_DIR, "correlation_matrix.csv")
corr_png = os.path.join(ANALYSIS_DIR, "correlation_matrix.png")
corr_df.to_csv(corr_csv)
plt.figure(figsize=(8, 6))
sns.heatmap(corr_df, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1)
plt.title("Chili/Eggplant Feature Correlation Matrix")
plt.tight_layout()
plt.savefig(corr_png, dpi=150)
plt.close()
print("Saved correlation matrix to", corr_csv, "and", corr_png)

# =====================================================
# LABEL ENCODING
# =====================================================
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)
joblib.dump(encoder, os.path.join(OUT_DIR, "label_encoder.save"))
print("Saved label encoder")

# =====================================================
# TRAIN / VALIDATION / TEST SPLIT
# =====================================================
X_train, X_temp, y_train, y_temp = train_test_split(
    X,
    y_encoded,
    test_size=0.30,
    stratify=y_encoded,
    random_state=SEED,
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp,
    y_temp,
    test_size=0.50,
    stratify=y_temp,
    random_state=SEED,
)

# =====================================================
# SCALING
# =====================================================
scaler = MinMaxScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)
joblib.dump(scaler, os.path.join(OUT_DIR, "scaler.save"))
print("Saved scaler")

# One-hot encoding for categorical loss.
y_train_oh = to_categorical(y_train, num_classes=len(encoder.classes_))
y_val_oh = to_categorical(y_val, num_classes=len(encoder.classes_))
y_test_oh = to_categorical(y_test, num_classes=len(encoder.classes_))

# =====================================================
# MODEL DEFINITION
# =====================================================
model = Sequential(
    [
        Dense(128, input_dim=X_train_scaled.shape[1], activation="relu"),
        Dropout(0.15),
        Dense(128, activation="relu"),
        Dense(64, activation="relu"),
        Dense(len(encoder.classes_), activation="softmax"),
    ]
)

model.compile(
    optimizer=Adam(learning_rate=0.0008),
    loss="categorical_crossentropy",
    metrics=["accuracy"],
)

model.summary()

checkpoint_path = os.path.join(OUT_DIR, "best_model.keras")
callbacks = [
    EarlyStopping(monitor="val_accuracy", patience=12, restore_best_weights=True, verbose=1),
    ModelCheckpoint(checkpoint_path, monitor="val_accuracy", save_best_only=True, verbose=1),
]

# =====================================================
# TRAINING
# =====================================================
print("Training Chili/Eggplant ANN...")
history = model.fit(
    X_train_scaled,
    y_train_oh,
    validation_data=(X_val_scaled, y_val_oh),
    epochs=100,
    batch_size=64,
    callbacks=callbacks,
    verbose=1,
)

# =====================================================
# SAVE FINAL MODEL
# =====================================================
final_keras_path = os.path.join(OUT_DIR, "chili_eggplant_model.keras")
final_h5_path = os.path.join(OUT_DIR, "chili_eggplant_model.h5")
model.save(final_keras_path)
try:
    model.save(final_h5_path)
except Exception as exc:
    print(f"Could not save HDF5 copy: {exc}")

print("Saved model artifacts to", OUT_DIR)

# =====================================================
# EVALUATION
# =====================================================
probabilities = model.predict(X_test_scaled, verbose=0)
y_pred = np.argmax(probabilities, axis=1)
y_true = np.argmax(y_test_oh, axis=1)

acc = accuracy_score(y_true, y_pred)
print(f"\nTest accuracy: {acc:.4f}")
print("\nClassification report:\n")
print(classification_report(y_true, y_pred, target_names=list(encoder.classes_)))

# =====================================================
# ANALYSIS ARTIFACTS
# =====================================================
cm = confusion_matrix(y_true, y_pred)
cm_df = pd.DataFrame(cm, index=encoder.classes_, columns=encoder.classes_)
cm_csv = os.path.join(ANALYSIS_DIR, "confusion_matrix.csv")
cm_png = os.path.join(ANALYSIS_DIR, "confusion_matrix.png")
cm_df.to_csv(cm_csv)

plt.figure(figsize=(6, 5))
sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues")
plt.title("Chili/Eggplant Confusion Matrix")
plt.ylabel("True")
plt.xlabel("Predicted")
plt.tight_layout()
plt.savefig(cm_png, dpi=150)
plt.close()

report = classification_report(y_true, y_pred, target_names=list(encoder.classes_), output_dict=True)
report_df = pd.DataFrame(report).transpose()
report_csv = os.path.join(ANALYSIS_DIR, "classification_report.csv")
report_df.to_csv(report_csv)

summary = {
    "accuracy": float(acc),
    "classes": list(encoder.classes_),
    "n_train": int(len(X_train_scaled)),
    "n_val": int(len(X_val_scaled)),
    "n_test": int(len(X_test_scaled)),
    "feature_names": FEATURE_NAMES,
    "final_model_keras": final_keras_path,
    "final_model_h5": final_h5_path,
}
with open(os.path.join(ANALYSIS_DIR, "summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)

# Training curves
history_df = pd.DataFrame(history.history)
history_csv = os.path.join(ANALYSIS_DIR, "training_history.csv")
history_df.to_csv(history_csv, index=False)

plt.figure(figsize=(8, 5))
plt.plot(history.history.get("accuracy", []), label="train_accuracy")
plt.plot(history.history.get("val_accuracy", []), label="val_accuracy")
plt.title("Training Accuracy")
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS_DIR, "training_accuracy.png"), dpi=150)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(history.history.get("loss", []), label="train_loss")
plt.plot(history.history.get("val_loss", []), label="val_loss")
plt.title("Training Loss")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS_DIR, "training_loss.png"), dpi=150)
plt.close()

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].plot(history.history.get("accuracy", []), label="train_accuracy")
axes[0].plot(history.history.get("val_accuracy", []), label="val_accuracy")
axes[0].set_title("Accuracy")
axes[0].set_xlabel("Epoch")
axes[0].set_ylabel("Accuracy")
axes[0].legend()

axes[1].plot(history.history.get("loss", []), label="train_loss")
axes[1].plot(history.history.get("val_loss", []), label="val_loss")
axes[1].set_title("Loss")
axes[1].set_xlabel("Epoch")
axes[1].set_ylabel("Loss")
axes[1].legend()

plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS_DIR, "accuracy_loss.png"), dpi=150)
plt.close()

print("Saved analysis artifacts to", ANALYSIS_DIR)

# =====================================================
# PERFORMANCE REPORT
# =====================================================
report_path = os.path.join(ANALYSIS_DIR, "performance_report.md")
report_lines = [
    "# Chili/Eggplant Model Performance Report",
    "",
    "## Training Summary",
    f"- Dataset: `{DATA_PATH}`",
    f"- Total samples: `{len(df)}`",
    f"- Training samples: `{len(X_train_scaled)}`",
    f"- Validation samples: `{len(X_val_scaled)}`",
    f"- Test samples: `{len(X_test_scaled)}`",
    f"- Classes: `{', '.join(list(encoder.classes_))}`",
    f"- Test accuracy: `{acc:.4f}`",
    "",
    "## Evaluation Artifacts",
    f"- Confusion matrix CSV: `{cm_csv}`",
    f"- Confusion matrix image: `{cm_png}`",
    f"- Correlation matrix CSV: `{corr_csv}`",
    f"- Correlation matrix image: `{corr_png}`",
    f"- Accuracy/Loss plot: `{os.path.join(ANALYSIS_DIR, 'accuracy_loss.png')}`",
    f"- Training accuracy plot: `{os.path.join(ANALYSIS_DIR, 'training_accuracy.png')}`",
    f"- Training loss plot: `{os.path.join(ANALYSIS_DIR, 'training_loss.png')}`",
    "",
    "## Saved Model Files",
    f"- Final Keras model: `{final_keras_path}`",
    f"- Final H5 model: `{final_h5_path}`",
    f"- Label encoder: `{os.path.join(OUT_DIR, 'label_encoder.save')}`",
    f"- Scaler: `{os.path.join(OUT_DIR, 'scaler.save')}`",
    "",
    "## Notes",
    "- The training script keeps `model_training.py` untouched.",
    "- Use the saved `label_encoder.save` and `scaler.save` for inference.",
]
with open(report_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(report_lines) + "\n")

print("Saved performance report to", report_path)

# =====================================================
# CANONICAL CHECK
# =====================================================
print("\nCanonical midpoint predictions:")
canonical_rows = {
    "Chili": [60.0, 50.0, 210.0, 6.2, 68.0, 27.0],
    "Eggplant": [78.0, 52.0, 230.0, 6.3, 66.0, 26.0],
}
for crop_name, values in canonical_rows.items():
    pred = model.predict(scaler.transform([values]), verbose=0)
    predicted_label = encoder.inverse_transform([int(np.argmax(pred[0]))])[0]
    print(f"{crop_name}: predicted -> {predicted_label}")

print("Done.")
