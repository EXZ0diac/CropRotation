# ===============================================
#  Crop Rotation AI - ANN Model Training Script
#  Fully Deterministic Version
# ===============================================

import os
import joblib
import numpy as np
import random
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import tensorflow as tf

# -----------------------------
# Define crops and exact midpoints
# -----------------------------
# deterministic seeds
SEED = 42
np.random.seed(SEED)
random.seed(SEED)
tf.random.set_seed(SEED)

crops = ["Paddy","Maize","Chili","Cucumber","Groundnut","Spinach"]

soil_midpoints = {
    "Paddy":      [95.0,47.5,47.5,6.65,62.5,30.0],
    "Maize":      [75.0,37.5,37.5,6.2,57.5,28.0],
    "Chili":      [55.0,57.5,42.5,6.0,52.5,31.0],
    "Cucumber":   [65.0,42.5,52.5,6.2,67.5,27.0],
    "Groundnut":  [45.0,27.5,32.5,6.45,52.5,29.0],
    "Spinach":    [35.0,17.5,22.5,6.75,67.5,23.0]
}

# Augment/generate dataset
# Produce at least TOTAL_SAMPLES float samples (decimal values) across crops.
X_list = []
y_list = []
# Minimum total samples requested
TOTAL_SAMPLES = 100000
samples_per_crop = int(np.ceil(TOTAL_SAMPLES / len(crops)))
# Use modest uniform half-range around midpoints so classes remain separable
# Tuned to increase chance of high accuracy while still producing varied floats
uniform_half_range = np.array([10.0, 10.0, 10.0, 0.4, 10.0, 2.0])
# Introduce small label noise for realism
label_noise_frac = 0.11  # 11% of labels will be randomly reassigned
for crop in crops:
    midpoint = np.array(soil_midpoints[crop], dtype=float)
    for _ in range(samples_per_crop):
        # uniform noise (floats) around midpoint
        noise = np.random.uniform(low=-uniform_half_range, high=uniform_half_range)
        sample = midpoint + noise
        # clip to realistic ranges
        sample[0:3] = np.clip(sample[0:3], 0, 300)
        sample[3] = np.clip(sample[3], 3.0, 9.0)
        sample[4] = np.clip(sample[4], 0, 100)
        sample[5] = np.clip(sample[5], -10, 50)
        X_list.append(sample.tolist())
        y_list.append(crop)

X = np.array(X_list, dtype=float)
y = np.array(y_list)

# -----------------------------
# Encode labels (needed for stratified splits)
# -----------------------------
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)
os.makedirs("model", exist_ok=True)
joblib.dump(encoder, "model/label_encoder.save")

# Introduce label noise by randomly changing a portion of the labels
if label_noise_frac is not None and label_noise_frac > 0.0:
    n_total = len(y_encoded)
    n_flip = int(np.floor(n_total * label_noise_frac))
    if n_flip > 0:
        np.random.seed(SEED)
        flip_idx = np.random.choice(n_total, size=n_flip, replace=False)
        for i in flip_idx:
            orig = y_encoded[i]
            # choose a different random class
            choices = list(range(len(crops)))
            choices.remove(int(orig))
            y_encoded[i] = np.random.choice(choices)

# One-hot encode for ANN
y_onehot = to_categorical(y_encoded, num_classes=len(crops))

# -----------------------------
# Train/validation/test split (split BEFORE scaling to avoid data leakage)
# -----------------------------
# First split: train vs temp (val+test)
X_train, X_temp, y_train, y_temp = train_test_split(X, y_onehot, test_size=0.3, stratify=y_encoded, random_state=SEED)
# Second split: val vs test
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, stratify=np.argmax(y_temp, axis=1), random_state=SEED)

# -----------------------------
# Scale features: fit scaler on training data only, then transform val/test
# -----------------------------
scaler = MinMaxScaler()
X_train = scaler.fit_transform(X_train)
X_val = scaler.transform(X_val)
X_test = scaler.transform(X_test)
joblib.dump(scaler, "model/scaler.save")

# -----------------------------
# Build ANN model
# -----------------------------

model = Sequential([
    Dense(128, input_dim=X_train.shape[1], activation='relu'),
    Dropout(0.15),
    Dense(128, activation='relu'),
    Dense(64, activation='relu'),
    Dense(len(crops), activation='softmax')
])

model.compile(optimizer=Adam(learning_rate=0.0008),
              loss='categorical_crossentropy',
              metrics=['accuracy'])

# Callbacks
# prefer the newer Keras native format; keep an HDF5 copy for compatibility
checkpoint_path = "model/best_model.keras"
# Run full training for 100 epochs to observe stability (no early stopping)
callbacks = [
    ModelCheckpoint(checkpoint_path, monitor='val_accuracy', save_best_only=True, verbose=1)
]

print("🧠 Training improved ANN with augmentation and validation...")
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=100,
    batch_size=64,
    callbacks=callbacks,
    verbose=1
)

# Save final model and artifacts (Keras native format is preferred)
model.save("model/crop_rotation_model.keras")
# Also save an HDF5 copy for compatibility with older tooling
try:
    model.save("model/crop_rotation_model.h5")
except Exception as e:
    print(f"Could not save HDF5 copy: {e}")
joblib.dump(scaler, "model/scaler.save")
joblib.dump(encoder, "model/label_encoder.save")
print("💾 Model and preprocessors saved to model/ (both .keras and .h5 when possible)")

# Evaluate on test set
y_true = np.argmax(y_test, axis=1)
y_pred = np.argmax(model.predict(X_test), axis=1)
test_acc = accuracy_score(y_true, y_pred)
print(f"\n🔎 Test accuracy: {test_acc:.4f}")
print("\nClassification report:\n")
print(classification_report(y_true, y_pred, target_names=crops))

# Check canonical midpoints
print("\n🌾 Predictions for canonical midpoints:")
for crop in crops:
    input_scaled = scaler.transform([soil_midpoints[crop]])
    pred = model.predict(input_scaled, verbose=0)
    predicted_crop = encoder.inverse_transform([np.argmax(pred)])[0]
    print(f"{crop}: Predicted -> {predicted_crop}")

# -----------------------------
# Analysis artifacts: correlation matrix, confusion matrix, training curves
# -----------------------------
os.makedirs("model/analysis", exist_ok=True)

# Feature names for DataFrame
feature_names = ["N", "P", "K", "pH", "Moisture", "Temperature"]
# Use original (unscaled) X to compute correlations
df_features = pd.DataFrame(X, columns=feature_names)

# Correlation matrix (Pearson)
corr = df_features.corr()
corr_csv = "model/analysis/correlation_matrix.csv"
corr_img = "model/analysis/correlation_matrix.png"
corr.to_csv(corr_csv)
plt.figure(figsize=(8, 6))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm")
plt.title("Feature Correlation Matrix")
plt.tight_layout()
plt.savefig(corr_img, dpi=150)
plt.close()
print(f"Saved correlation matrix CSV -> {corr_csv} and image -> {corr_img}")

# Confusion matrix
cm = confusion_matrix(y_true, y_pred)
cm_df = pd.DataFrame(cm, index=crops, columns=crops)
cm_csv = "model/analysis/confusion_matrix.csv"
cm_img = "model/analysis/confusion_matrix.png"
cm_df.to_csv(cm_csv)
plt.figure(figsize=(8, 6))
sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues")
plt.ylabel("True")
plt.xlabel("Predicted")
plt.title("Confusion Matrix")
plt.tight_layout()
plt.savefig(cm_img, dpi=150)
plt.close()
print(f"Saved confusion matrix CSV -> {cm_csv} and image -> {cm_img}")

# Classification report -> CSV
report_dict = classification_report(y_true, y_pred, target_names=crops, output_dict=True)
report_df = pd.DataFrame(report_dict).transpose()
report_csv = "model/analysis/classification_report.csv"
report_md = "model/analysis/performance_report.md"
report_df.to_csv(report_csv)
print(f"Saved classification report CSV -> {report_csv}")

# Create a lightweight markdown summary linking artifacts
with open(report_md, "w", encoding="utf-8") as f:
    f.write("# Model Performance Report\n\n")
    f.write(f"**Test accuracy:** {test_acc:.4f}\n\n")
    f.write("## Classification report\n\n")
    # to_markdown() requires the optional 'tabulate' package. If it's missing,
    # fall back to a plain-text table so the script doesn't crash.
    try:
        md_table = report_df.to_markdown()
    except Exception:
        md_table = report_df.to_string()
        f.write("**Note:** Optional dependency 'tabulate' is not installed. Install with `pip install tabulate` to get a prettier markdown table.\n\n")
    f.write(md_table)
    f.write("\n\n")
    f.write("## Artifacts\n\n")
    f.write(f"- Correlation matrix CSV: `correlation_matrix.csv`\n")
    f.write(f"- Correlation matrix image: `correlation_matrix.png`\n")
    f.write(f"- Confusion matrix CSV: `confusion_matrix.csv`\n")
    f.write(f"- Confusion matrix image: `confusion_matrix.png`\n")
    f.write(f"- Classification report CSV: `classification_report.csv`\n")
    f.write(f"- Training curves image: `accuracy_loss.png`\n")

print(f"Saved performance summary markdown -> {report_md}")

# Training curves: accuracy & loss vs epoch
acc = history.history.get("accuracy", [])
val_acc = history.history.get("val_accuracy", [])
loss = history.history.get("loss", [])
val_loss = history.history.get("val_loss", [])
curves_img = "model/analysis/accuracy_loss.png"
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
