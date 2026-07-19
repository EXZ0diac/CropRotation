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
import argparse

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tensorflow as tf  # type: ignore
from sklearn.metrics import (
    accuracy_score,
    auc,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    roc_curve,
)
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
EPOCHS = 100
# Choose which class to treat as the "positive" class for ROC/threshold sweeps
POSITIVE_CLASS = "Chili"
TUNE = False

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# ------------------------
# CLI args
# ------------------------
parser = argparse.ArgumentParser(description="Train/evaluate Chili/Eggplant model")
parser.add_argument("--data", default=DATA_PATH, help="path to CSV dataset")
parser.add_argument("--epochs", type=int, default=EPOCHS, help="training epochs")
parser.add_argument("--tune", action="store_true", help="use tuned architecture/settings")
args = parser.parse_args()
DATA_PATH = args.data
EPOCHS = args.epochs
TUNE = args.tune

np.random.seed(SEED)
random.seed(SEED)
tf.random.set_seed(SEED)

# Feature names for the CSV file (adjust if your CSV differs)
FEATURE_NAMES = ["Nitrogen", "Phosphorus", "Potassium", "pH", "Humidity", "Temperature"]


def build_model(input_dim: int, num_classes: int, tune: bool = False) -> Sequential:
    """Builds and compiles the Keras model. When `tune=True` use a slightly different
    architecture and learning rate aimed at improving PR curves for tougher datasets."""
    if tune:
        m = Sequential(
            [
                Dense(256, input_dim=input_dim, activation="relu"),
                Dropout(0.25),
                Dense(192, activation="relu"),
                Dropout(0.20),
                Dense(128, activation="relu"),
                Dense(64, activation="relu"),
                Dense(num_classes, activation="softmax"),
            ]
        )
        opt = Adam(learning_rate=0.0006)
    else:
        m = Sequential(
            [
                Dense(128, input_dim=input_dim, activation="relu"),
                Dropout(0.15),
                Dense(128, activation="relu"),
                Dense(64, activation="relu"),
                Dense(num_classes, activation="softmax"),
            ]
        )
        opt = Adam(learning_rate=0.0008)

    m.compile(optimizer=opt, loss="categorical_crossentropy", metrics=["accuracy"])
    return m

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

# Normalize labels to expected casing (adjust map for your dataset as needed).
y = y.replace({"chili": "Chili", "eggplant": "Eggplant"})
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
model = build_model(X_train_scaled.shape[1], len(encoder.classes_), tune=TUNE)
model.summary()

checkpoint_path = os.path.join(OUT_DIR, "best_model.keras")
early_stopping = EarlyStopping(
    monitor="val_loss",
    patience=10,
    restore_best_weights=True,
    verbose=1,
)
callbacks = [
    ModelCheckpoint(checkpoint_path, monitor="val_accuracy", save_best_only=True, verbose=1),
    early_stopping,
]

# =====================================================
# TRAINING
# =====================================================
print("Training Chili/Eggplant ANN...")
history = model.fit(
    X_train_scaled,
    y_train_oh,
    validation_data=(X_val_scaled, y_val_oh),
    epochs=EPOCHS,
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

# ROC curve for the positive class to show threshold-independent performance.
roc_png = os.path.join(ANALYSIS_DIR, "roc_curve.png")
if len(encoder.classes_) >= 2:
    try:
        positive_class_index = int(list(encoder.classes_).index(POSITIVE_CLASS))
    except ValueError:
        positive_class_index = 0
    y_true_binary = y_test_oh[:, positive_class_index]
    fpr, tpr, _ = roc_curve(y_true_binary, probabilities[:, positive_class_index])
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, label=f"ROC curve (AUC = {roc_auc:.4f})")
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Chance")
    plt.title("ROC Curve")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(roc_png, dpi=150)
    plt.close()
else:
    roc_auc = None
    roc_png = None

# Precision-recall curve per class using one-vs-rest evaluation.
pr_png = os.path.join(ANALYSIS_DIR, "precision_recall_curve.png")
class_precision = {}
class_recall = {}
class_average_precision = {}

n_classes = len(encoder.classes_)
plt.figure(figsize=(7, 5))
colors = sns.color_palette("tab10", n_colors=max(3, n_classes))
for class_index, class_name in enumerate(encoder.classes_):
    precision, recall, _ = precision_recall_curve(y_test_oh[:, class_index], probabilities[:, class_index])
    average_precision = average_precision_score(y_test_oh[:, class_index], probabilities[:, class_index])
    class_precision[class_name] = precision.tolist()
    class_recall[class_name] = recall.tolist()
    class_average_precision[class_name] = float(average_precision)
    # plot per-class with distinct colors
    plt.plot(recall, precision, label=f"{class_name} {average_precision:.3f}", color=colors[class_index % len(colors)], linewidth=1.6)

# micro / all-classes curve (thicker emphasis like reference image)
all_precision, all_recall, _ = precision_recall_curve(y_test_oh.ravel(), probabilities.ravel())
micro_average_precision = float(average_precision_score(y_test_oh, probabilities, average="micro"))
macro_average_precision = float(average_precision_score(y_test_oh, probabilities, average="macro"))
mean_ap = macro_average_precision
plt.plot(all_recall, all_precision, linewidth=3.5, color="#0b61a4", label=f"all classes {mean_ap:.3f} mAP")

plt.title("Precision-Recall Curve")
plt.xlabel("Recall")
plt.ylabel("Precision")
plt.xlim(0, 1)
plt.ylim(0, 1.02)
plt.margins(x=0, y=0)
# place legend to the right like the reference; use bbox_to_anchor
plt.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))
plt.tight_layout()
plt.savefig(pr_png, dpi=150, bbox_inches="tight")
plt.close()

# Precision-confidence curve per class.
precision_confidence_png = os.path.join(ANALYSIS_DIR, "precision_confidence_curve.png")
recall_confidence_png = os.path.join(ANALYSIS_DIR, "recall_confidence_curve.png")
thresholds_pc = np.linspace(0.0, 1.0, 101)

if len(encoder.classes_) == 2:
    plt.figure(figsize=(8, 5))
    for class_index, class_name in enumerate(encoder.classes_):
        class_scores = probabilities[:, class_index]
        precision_values = []
        for threshold in thresholds_pc:
            predicted_positive = (class_scores >= threshold).astype(int)
            true_positive_mask = y_test_oh[:, class_index]
            tp = int(np.sum((predicted_positive == 1) & (true_positive_mask == 1)))
            fp = int(np.sum((predicted_positive == 1) & (true_positive_mask == 0)))
            precision_values.append(tp / (tp + fp) if (tp + fp) else 1.0)
        midpoint_index = int(np.argmin(np.abs(thresholds_pc - 0.5)))
        plt.plot(thresholds_pc, precision_values, label=f"{class_name} (P@0.50={precision_values[midpoint_index]:.3f})")
    plt.title("Precision-Confidence Curve")
    plt.xlabel("Confidence")
    plt.ylabel("Precision")
    plt.xlim(0, 1)
    plt.ylim(0, 1.02)
    plt.margins(x=0, y=0)
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(precision_confidence_png, dpi=150)
    plt.close()

    plt.figure(figsize=(8, 5))
    for class_index, class_name in enumerate(encoder.classes_):
        class_scores = probabilities[:, class_index]
        recall_values = []
        for threshold in thresholds_pc:
            predicted_positive = (class_scores >= threshold).astype(int)
            true_positive_mask = y_test_oh[:, class_index]
            tp = int(np.sum((predicted_positive == 1) & (true_positive_mask == 1)))
            fn = int(np.sum((predicted_positive == 0) & (true_positive_mask == 1)))
            recall_values.append(tp / (tp + fn) if (tp + fn) else 0.0)
        midpoint_index = int(np.argmin(np.abs(thresholds_pc - 0.5)))
        plt.plot(thresholds_pc, recall_values, label=f"{class_name} (R@0.50={recall_values[midpoint_index]:.3f})")
    plt.title("Recall-Confidence Curve")
    plt.xlabel("Confidence")
    plt.ylabel("Recall")
    plt.xlim(0, 1)
    plt.ylim(0, 1.02)
    plt.margins(x=0, y=0)
    plt.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(recall_confidence_png, dpi=150)
    plt.close()
else:
    precision_confidence_png = None
    recall_confidence_png = None

# Threshold sweeps for F1-score and accuracy.
try:
    positive_class_index = int(list(encoder.classes_).index(POSITIVE_CLASS))
except ValueError:
    positive_class_index = 0
score_column = probabilities[:, positive_class_index]
thresholds = np.linspace(0.0, 1.0, 101)
f1_scores = []
threshold_accuracies = []

# Use binary true labels for the selected positive class to compute thresholds correctly
y_true_binary = y_test_oh[:, positive_class_index]
for threshold in thresholds:
    y_threshold_pred = (score_column >= threshold).astype(int)
    f1_scores.append(f1_score(y_true_binary, y_threshold_pred))
    threshold_accuracies.append(accuracy_score(y_true_binary, y_threshold_pred))

metrics_df = pd.DataFrame(
    {
        "threshold": thresholds,
        "f1_score": f1_scores,
        "accuracy": threshold_accuracies,
    }
)
metrics_csv = os.path.join(ANALYSIS_DIR, "threshold_metrics.csv")
metrics_df.to_csv(metrics_csv, index=False)

best_f1_index = int(np.argmax(f1_scores))
best_accuracy_index = int(np.argmax(threshold_accuracies))
best_f1_threshold = float(thresholds[best_f1_index])
best_f1_value = float(f1_scores[best_f1_index])
best_accuracy_threshold = float(thresholds[best_accuracy_index])
best_accuracy_value = float(threshold_accuracies[best_accuracy_index])

plt.figure(figsize=(8, 5))
plt.plot(thresholds, f1_scores, label="F1-score", color="#1f77b4")
plt.axvline(best_f1_threshold, linestyle="--", color="#1f77b4", alpha=0.5)
plt.title("F1-Score vs Confidence Threshold")
plt.xlabel("Confidence")
plt.ylabel("F1-score")
plt.ylim(0, 1.02)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS_DIR, "f1_score_curve.png"), dpi=150)
plt.close()

plt.figure(figsize=(8, 5))
plt.plot(thresholds, threshold_accuracies, label="Accuracy", color="#d62728")
plt.axvline(best_accuracy_threshold, linestyle="--", color="#d62728", alpha=0.5)
plt.title("Accuracy vs Confidence Threshold")
plt.xlabel("Confidence")
plt.ylabel("Accuracy")
plt.ylim(0, 1.02)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS_DIR, "accuracy_curve.png"), dpi=150)
plt.close()

report = classification_report(y_true, y_pred, target_names=list(encoder.classes_), output_dict=True)
report_df = pd.DataFrame(report).transpose()
report_csv = os.path.join(ANALYSIS_DIR, "classification_report.csv")
report_df.to_csv(report_csv)

summary = {
    "accuracy": float(acc),
    "roc_auc": None if roc_auc is None else float(roc_auc),
    "average_precision_micro": None if micro_average_precision is None else float(micro_average_precision),
    "average_precision_macro": None if macro_average_precision is None else float(macro_average_precision),
    "average_precision_per_class": class_average_precision,
    "best_f1_score": best_f1_value,
    "best_f1_threshold": best_f1_threshold,
    "best_threshold_accuracy": best_accuracy_value,
    "best_threshold_accuracy_threshold": best_accuracy_threshold,
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
    f"- ROC AUC: `{roc_auc:.4f}`" if roc_auc is not None else "- ROC AUC: not available",
    f"- Average precision (micro): `{micro_average_precision:.4f}`" if micro_average_precision is not None else "- Average precision (micro): not available",
    f"- Average precision (macro): `{macro_average_precision:.4f}`" if macro_average_precision is not None else "- Average precision (macro): not available",
    f"- Best F1-score: `{best_f1_value:.4f}` at threshold `{best_f1_threshold:.2f}`",
    f"- Best threshold accuracy: `{best_accuracy_value:.4f}` at threshold `{best_accuracy_threshold:.2f}`",
    "",
    "## Evaluation Artifacts",
    f"- Confusion matrix CSV: `{cm_csv}`",
    f"- Confusion matrix image: `{cm_png}`",
    f"- ROC curve image: `{roc_png}`" if roc_png else "- ROC curve image: not generated for non-binary classification",
    f"- Precision-recall curve image: `{pr_png}`" if pr_png else "- Precision-recall curve image: not generated for non-binary classification",
    f"- Precision-confidence curve image: `{precision_confidence_png}`" if precision_confidence_png else "- Precision-confidence curve image: not generated for non-binary classification",
    f"- Recall-confidence curve image: `{recall_confidence_png}`" if recall_confidence_png else "- Recall-confidence curve image: not generated for non-binary classification",
    f"- Average precision per class: `{class_average_precision}`" if class_average_precision else "- Average precision per class: not available",
    f"- F1-score curve image: `{os.path.join(ANALYSIS_DIR, 'f1_score_curve.png')}`",
    f"- Accuracy curve image: `{os.path.join(ANALYSIS_DIR, 'accuracy_curve.png')}`",
    f"- Threshold metrics CSV: `{metrics_csv}`",
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
