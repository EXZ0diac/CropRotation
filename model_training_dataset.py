# ===============================================
#  Crop Rotation AI - Dataset-based Training Script
#  Uses `datacore.csv` as input dataset
# ===============================================

import os
import joblib
import numpy as np
import random
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# deterministic seeds
SEED = 42
np.random.seed(SEED)
random.seed(SEED)
tf.random.set_seed(SEED)

# Paths and output directories
DATA_PATH = "datacore.csv"
OUT_DIR = "model_dataset"
ANALYSIS_DIR = os.path.join(OUT_DIR, "analysis")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# Attempt to load CSV
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"Dataset file not found: {DATA_PATH}")

print(f"Loading dataset from {DATA_PATH}...")
df = pd.read_csv(DATA_PATH)
print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")

# Normalize column names to lowercase for matching
colmap = {c.lower(): c for c in df.columns}
cols_lower = [c.lower() for c in df.columns]

# Helper to find a column by keyword
def find_col(keywords):
    for kw in keywords:
        for c in df.columns:
            if kw.lower() in c.lower():
                return c
    return None

# Map expected features using common keywords
col_N = find_col(["nitro", "n ", "n,", "n(", "nitrogen"]) or find_col(["n"]) if False else find_col(["nitrogen", "nitro"])
col_P = find_col(["phosph", "phosphor", "phosphorous", "phosphorus", "p ", "p(", "phos"]) or find_col(["p"])
col_K = find_col(["potass", "potassium", "k ", "k(", "kalium"]) or find_col(["k"])
col_temp = find_col(["temp", "temperature", "temparature", "temperaturec"])
col_hum = find_col(["humid", "humidity"])
col_moist = find_col(["moist", "moisture"])
col_crop = find_col(["crop", "crop type", "crop_type", "label", "target"])

# Fallback: try common short names
if col_N is None and "n" in cols_lower:
    col_N = [c for c in df.columns if c.lower() == "n"][0]
if col_P is None and "p" in cols_lower:
    col_P = [c for c in df.columns if c.lower() == "p"][0]
if col_K is None and "k" in cols_lower:
    col_K = [c for c in df.columns if c.lower() == "k"][0]

# Validate required columns
required = {
    "N": colmap.get(col_N.lower()) if col_N else None,
    "P": colmap.get(col_P.lower()) if col_P else None,
    "K": colmap.get(col_K.lower()) if col_K else None,
    "Temperature": colmap.get(col_temp.lower()) if col_temp else None,
    "Humidity": colmap.get(col_hum.lower()) if col_hum else None,
    "Moisture": colmap.get(col_moist.lower()) if col_moist else None,
    "Crop": colmap.get(col_crop.lower()) if col_crop else None,
}

missing = [k for k, v in required.items() if v is None]
if missing:
    raise RuntimeError(f"Could not find required columns in {DATA_PATH}. Missing: {missing}. Found columns: {list(df.columns)}")

print("Using columns:")
for k, v in required.items():
    print(f"  {k}: {v}")

# Build feature matrix X and label vector y
feature_cols = [required["N"], required["P"], required["K"], required["Temperature"], required["Humidity"], required["Moisture"]]
X_df = df[feature_cols].copy()

# Ensure numeric parsing (allow decimal points). Do NOT treat zeros as missing
# — zeros are valid values (user may not have applied fertilizer).
for c in feature_cols:
    # coerce errors to NaN so we can drop invalid rows, but keep 0.0 as valid
    X_df[c] = pd.to_numeric(X_df[c], errors='coerce')

# Prepare label column, strip whitespace
y_series = df[required["Crop"]].astype(str).str.strip().copy()

# Drop rows with missing values in features or label
before = len(X_df)
mask = X_df.notnull().all(axis=1) & y_series.notnull()
X_df = X_df[mask]
y_series = y_series[mask]
after = len(X_df)
if after < before:
    print(f"Dropped {before-after} rows with missing values")

X = X_df.values.astype(float)
y = y_series.values

# Scale features
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)
joblib.dump(scaler, os.path.join(OUT_DIR, "scaler.save"))

# Encode labels
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)
joblib.dump(encoder, os.path.join(OUT_DIR, "label_encoder.save"))

# One-hot for ANN
y_onehot = to_categorical(y_encoded, num_classes=len(encoder.classes_))

# Train/val/test split
X_train, X_temp, y_train, y_temp = train_test_split(X_scaled, y_onehot, test_size=0.3, stratify=y_encoded, random_state=SEED)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, stratify=np.argmax(y_temp, axis=1), random_state=SEED)

# Build model (input dim = number of features)
input_dim = X_scaled.shape[1]
model = Sequential([
    Dense(128, input_dim=input_dim, activation='relu'),
    Dropout(0.15),
    Dense(128, activation='relu'),
    Dense(64, activation='relu'),
    Dense(len(encoder.classes_), activation='softmax')
])

model.compile(optimizer=Adam(learning_rate=0.0008), loss='categorical_crossentropy', metrics=['accuracy'])

# Callbacks
checkpoint_path = os.path.join(OUT_DIR, "best_model.keras")
callbacks = [
    EarlyStopping(monitor='val_accuracy', patience=15, restore_best_weights=True, verbose=1),
    ModelCheckpoint(checkpoint_path, monitor='val_accuracy', save_best_only=True, verbose=1)
]

print("Training model on dataset...")
history = model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=200, batch_size=64, callbacks=callbacks, verbose=1)

# Save model and artifacts
model.save(os.path.join(OUT_DIR, "crop_rotation_model.keras"))
try:
    model.save(os.path.join(OUT_DIR, "crop_rotation_model.h5"))
except Exception as e:
    print(f"Could not save HDF5 copy: {e}")
joblib.dump(scaler, os.path.join(OUT_DIR, "scaler.save"))
joblib.dump(encoder, os.path.join(OUT_DIR, "label_encoder.save"))
print(f"Saved model and preprocessors to {OUT_DIR}/")

# Evaluate
y_true = np.argmax(y_test, axis=1)
y_pred = np.argmax(model.predict(X_test), axis=1)
test_acc = accuracy_score(y_true, y_pred)
print(f"Test accuracy: {test_acc:.4f}")
print("Classification report:\n")
print(classification_report(y_true, y_pred, target_names=list(encoder.classes_)))

# Analysis artifacts
feature_names = ["N", "P", "K", "Temperature", "Humidity", "Moisture"]
df_features = pd.DataFrame(X, columns=feature_names)

# Correlation
corr = df_features.corr()
corr_csv = os.path.join(ANALYSIS_DIR, "correlation_matrix.csv")
corr_img = os.path.join(ANALYSIS_DIR, "correlation_matrix.png")
corr.to_csv(corr_csv)
plt.figure(figsize=(8, 6))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm")
plt.title("Feature Correlation Matrix")
plt.tight_layout()
plt.savefig(corr_img, dpi=150)
plt.close()
print(f"Saved correlation matrix -> {corr_csv}, {corr_img}")

# Confusion matrix
cm = confusion_matrix(y_true, y_pred)
cm_df = pd.DataFrame(cm, index=encoder.classes_, columns=encoder.classes_)
cm_csv = os.path.join(ANALYSIS_DIR, "confusion_matrix.csv")
cm_img = os.path.join(ANALYSIS_DIR, "confusion_matrix.png")
cm_df.to_csv(cm_csv)
plt.figure(figsize=(8, 6))
sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues")
plt.ylabel("True")
plt.xlabel("Predicted")
plt.title("Confusion Matrix")
plt.tight_layout()
plt.savefig(cm_img, dpi=150)
plt.close()
print(f"Saved confusion matrix -> {cm_csv}, {cm_img}")

# Classification report CSV + markdown summary
report_dict = classification_report(y_true, y_pred, target_names=list(encoder.classes_), output_dict=True)
report_df = pd.DataFrame(report_dict).transpose()
report_csv = os.path.join(ANALYSIS_DIR, "classification_report.csv")
report_md = os.path.join(ANALYSIS_DIR, "performance_report.md")
report_df.to_csv(report_csv)

with open(report_md, "w", encoding="utf-8") as f:
    f.write("# Model Performance Report\n\n")
    f.write(f"**Test accuracy:** {test_acc:.4f}\n\n")
    f.write("## Classification report\n\n")
    try:
        md_table = report_df.to_markdown()
    except Exception:
        md_table = report_df.to_string()
        f.write("**Note:** Optional dependency 'tabulate' not installed; install with `pip install tabulate` for prettier tables.\n\n")
    f.write(md_table)
    f.write("\n\n")
    f.write("## Artifacts\n\n")
    f.write(f"- Correlation matrix CSV: `correlation_matrix.csv`\n")
    f.write(f"- Correlation matrix image: `correlation_matrix.png`\n")
    f.write(f"- Confusion matrix CSV: `confusion_matrix.csv`\n")
    f.write(f"- Confusion matrix image: `confusion_matrix.png`\n")
    f.write(f"- Classification report CSV: `classification_report.csv`\n")
    f.write(f"- Training curves image: `accuracy_loss.png`\n")

print(f"Saved classification report CSV -> {report_csv} and summary -> {report_md}")

# Training curves
acc = history.history.get("accuracy", [])
val_acc = history.history.get("val_accuracy", [])
loss = history.history.get("loss", [])
val_loss = history.history.get("val_loss", [])
curves_img = os.path.join(ANALYSIS_DIR, "accuracy_loss.png")
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(acc, label="train_acc")
plt.plot(val_acc, label="val_acc")
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.legend()
plt.title("Accuracy vs Epoch")

plt.subplot(1, 2, 2)
plt.plot(loss, label="train_loss")
plt.plot(val_loss, label="val_loss")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.legend()
plt.title("Loss vs Epoch")

plt.tight_layout()
plt.savefig(curves_img, dpi=150)
plt.close()
print(f"Saved training curves -> {curves_img}")
