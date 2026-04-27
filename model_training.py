# ===============================================
#  Crop Rotation AI - ANN Model Training Script
#  Fully Deterministic Version
# ===============================================
# This script trains an Artificial Neural Network (ANN) to predict optimal crops
# based on soil properties. It includes comprehensive data generation, validation,
# and analysis with full reproducibility through fixed random seeds.

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

# =====================================================
# CONFIGURATION & DETERMINISTIC SETUP
# =====================================================
# Set fixed random seeds to ensure reproducible results across all libraries
# This guarantees the same training outcomes on every run (no randomness variation)
SEED = 42
np.random.seed(SEED)           # NumPy random seed
random.seed(SEED)              # Python built-in random seed
tf.random.set_seed(SEED)       # TensorFlow random seed

# Define the crop types that the model will classify/predict
crops = ["Paddy","Maize","Chili","Cucumber","Groundnut","Spinach"]

# Define optimal soil property midpoints for each crop
# Features: [N (Nitrogen), P (Phosphorus), K (Potassium), pH, Moisture, Temperature]
# These represent ideal soil conditions for maximum yield of each crop
soil_midpoints = {
    "Paddy":      [95.0,47.5,47.5,6.65,62.5,30.0],
    "Maize":      [75.0,37.5,37.5,6.2,57.5,28.0],
    "Chili":      [55.0,57.5,42.5,6.0,52.5,31.0],
    "Cucumber":   [65.0,42.5,52.5,6.2,67.5,27.0],
    "Groundnut":  [45.0,27.5,32.5,6.45,52.5,29.0],
    "Spinach":    [35.0,17.5,22.5,6.75,67.5,23.0]
}

# =====================================================
# SYNTHETIC DATASET GENERATION
# =====================================================
# Generate synthetic training data by creating samples around each crop's optimal midpoint.
# This approach creates a balanced, diverse dataset with controlled variations.

X_list = []  # Feature matrix (soil properties)
y_list = []  # Label vector (crop types)

# Configuration for dataset size
TOTAL_SAMPLES = 100000  # Target total number of synthetic samples
samples_per_crop = int(np.ceil(TOTAL_SAMPLES / len(crops)))  # Ensure balanced distribution

# Define the uniform noise range around each crop's midpoint.
# Larger values create more varied samples; tuned to maintain class separability.
# [N, P, K, pH, Moisture, Temperature] ranges
uniform_half_range = np.array([10.0, 10.0, 10.0, 0.4, 10.0, 2.0])

# Label noise introduces realistic imperfection: fraction of samples get wrong labels
# This helps prevent overfitting and improves model robustness
label_noise_frac = 0.11  # 11% label noise (deliberate mislabeling for robustness)

# Generate samples for each crop
for crop in crops:
    midpoint = np.array(soil_midpoints[crop], dtype=float)
    for _ in range(samples_per_crop):
        # Add uniform random noise around the midpoint (creates floating-point variation)
        noise = np.random.uniform(low=-uniform_half_range, high=uniform_half_range)
        sample = midpoint + noise
        
        # Clip values to realistic physical ranges to ensure valid soil properties
        sample[0:3] = np.clip(sample[0:3], 0, 300)        # N, P, K: 0-300 ppm
        sample[3] = np.clip(sample[3], 3.0, 9.0)          # pH: 3.0-9.0 (acidic to basic)
        sample[4] = np.clip(sample[4], 0, 100)            # Moisture: 0-100%
        sample[5] = np.clip(sample[5], -10, 50)           # Temperature: -10 to 50°C
        
        X_list.append(sample.tolist())
        y_list.append(crop)

# Convert lists to NumPy arrays for efficient computation
X = np.array(X_list, dtype=float)
y = np.array(y_list)

# =====================================================
# LABEL ENCODING & NOISE INJECTION
# =====================================================
# Convert categorical crop labels (strings) to numeric values (0-5) for neural network processing

# Initialize and fit LabelEncoder to map crop names to integers
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(y)

# Create model directory if it doesn't exist
os.makedirs("model", exist_ok=True)

# Save the encoder for later use during inference/prediction
joblib.dump(encoder, "model/label_encoder.save")

# Introduce controlled label noise to simulate real-world label errors
# This helps the model become more robust and not overfit to perfect labels
if label_noise_frac is not None and label_noise_frac > 0.0:
    n_total = len(y_encoded)
    n_flip = int(np.floor(n_total * label_noise_frac))  # Calculate number of labels to flip
    
    if n_flip > 0:
        np.random.seed(SEED)
        # Randomly select indices to flip (without replacement for uniqueness)
        flip_idx = np.random.choice(n_total, size=n_flip, replace=False)
        
        # Reassign selected labels to a different crop class
        for i in flip_idx:
            orig = y_encoded[i]
            # Create list of alternative classes (all except current one)
            choices = list(range(len(crops)))
            choices.remove(int(orig))
            # Randomly pick a different class
            y_encoded[i] = np.random.choice(choices)

# Convert encoded labels to one-hot vectors for categorical cross-entropy loss
# E.g., class 2 becomes [0, 0, 1, 0, 0, 0]
# This format is required by Keras for multi-class classification
y_onehot = to_categorical(y_encoded, num_classes=len(crops))

# =====================================================
# DATA SPLITTING: TRAIN / VALIDATION / TEST
# =====================================================
# Stratified split ensures each subset has representative distribution of all crop classes.
# Critical: Split BEFORE scaling to prevent data leakage between train/val/test sets.
# Data leakage occurs when information from test set influences training

# First split: 70% training, 30% temporary (for validation & test combined)
# stratify=y_encoded ensures class distribution is maintained in each fold
X_train, X_temp, y_train, y_temp = train_test_split(
    X, y_onehot, 
    test_size=0.3,                    # Reserve 30% for val+test
    stratify=y_encoded,                # Maintain crop distribution in each split
    random_state=SEED                  # Fixed seed for reproducibility
)

# Second split: divide the 30% equally into validation (15%) and test (15%)
# Extract original labels from one-hot vectors for stratification in second split
y_temp_encoded = np.argmax(y_temp, axis=1)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp,
    test_size=0.5,                     # Split 30% into 15% val and 15% test
    stratify=y_temp_encoded,           # Maintain distribution
    random_state=SEED
)

# =====================================================
# FEATURE SCALING (Normalization)
# =====================================================
# Normalize features to [0, 1] range using MinMaxScaler for better neural network performance.
# Neural networks train better on normalized data due to improved gradient flow.
# Critically important: Fit scaler ONLY on training data, then apply to val/test to prevent leakage.

# Fit scaler on training features and transform immediately
scaler = MinMaxScaler()
X_train = scaler.fit_transform(X_train)  # Learn scaling parameters from training data only

# Apply the same scaling transformation to validation and test data
# This ensures the model never "sees" the validation/test data during scaling
X_val = scaler.transform(X_val)
X_test = scaler.transform(X_test)

# Persist the scaler for use during inference on new data
joblib.dump(scaler, "model/scaler.save")

# =====================================================
# ARTIFICIAL NEURAL NETWORK MODEL ARCHITECTURE
# =====================================================
# Build a deep neural network for multi-class crop classification
# Architecture: Input -> Dense(128) -> Dropout -> Dense(128) -> Dense(64) -> Softmax Output
# This architecture balances model capacity with computational efficiency

model = Sequential([
    # First dense layer: 128 neurons with ReLU activation
    # input_dim=6 matches our 6 soil features (N, P, K, pH, Moisture, Temperature)
    # ReLU (Rectified Linear Unit) introduces non-linearity for complex decision boundaries
    Dense(128, input_dim=X_train.shape[1], activation='relu'),
    
    # Dropout layer (15%): Randomly deactivates 15% of neurons during training
    # Prevents overfitting and improves generalization by forcing redundancy
    Dropout(0.15),
    
    # Second dense layer: 128 neurons with ReLU activation (deeper feature extraction)
    # Processes the learned representations from first layer at higher abstraction
    Dense(128, activation='relu'),
    
    # Third dense layer: 64 neurons with ReLU activation (dimension reduction)
    # Reduces feature dimensionality before final classification layer
    Dense(64, activation='relu'),
    
    # Output layer: 6 neurons (one per crop) with softmax activation
    # Softmax converts raw scores (logits) into probability distribution (sums to 1)
    # Each output represents probability of that crop being optimal for given soil
    Dense(len(crops), activation='softmax')
])

# Compile model with optimizer, loss function, and metrics
# Compilation configures the model for training
model.compile(
    optimizer=Adam(learning_rate=0.0008),  # Adam optimizer with custom learning rate
                                            # Adam is adaptive and generally performs well
    loss='categorical_crossentropy',        # Standard loss for multi-class classification
                                            # Measures difference between predicted and true distributions
    metrics=['accuracy']                    # Track accuracy during training for monitoring
)

# =====================================================
# TRAINING CALLBACKS & CONFIGURATION
# =====================================================
# Define callbacks to monitor and improve training process
# Callbacks allow us to take actions at various stages of training

# checkpoint_path: Location to save the best model during training
checkpoint_path = "model/best_model.keras"

# ModelCheckpoint: Automatically save model when validation accuracy improves
# save_best_only=True ensures only the best epoch is kept (saves storage)
# This allows us to recover the best model even if later epochs overfit
callbacks = [
    ModelCheckpoint(checkpoint_path, monitor='val_accuracy', save_best_only=True, verbose=1)
]

# =====================================================
# MODEL TRAINING
# =====================================================
# Train the neural network on the augmented dataset
# Training is the process of adjusting weights to minimize loss on training data

print("🧠 Training improved ANN with augmentation and validation...")

# fit() performs the actual training loop
history = model.fit(
    X_train, y_train,                      # Training data (70% of total)
    validation_data=(X_val, y_val),        # Validation data for monitoring overfitting
                                            # Evaluated each epoch but doesn't affect weights
    epochs=100,                            # Train for 100 epochs (full passes through data)
    batch_size=64,                         # Process 64 samples at a time
                                            # Gradient updates happen after each batch
    callbacks=callbacks,                   # Apply monitoring callbacks
    verbose=1                              # Print progress for each epoch
)

# =====================================================
# MODEL & ARTIFACT PERSISTENCE
# =====================================================
# Save trained model and preprocessing objects for future inference

# Save final model in Keras native format (preferred modern format)
# .keras format is TensorFlow's native SavedModel format
model.save("model/crop_rotation_model.keras")

# Also save an HDF5 copy for compatibility with older systems/tooling
# HDF5 is an older format but widely supported
try:
    model.save("model/crop_rotation_model.h5")
except Exception as e:
    print(f"Could not save HDF5 copy: {e}")

# Re-save preprocessors (redundant but ensures consistency)
# These are essential for preprocessing new data before inference
joblib.dump(scaler, "model/scaler.save")
joblib.dump(encoder, "model/label_encoder.save")
print("💾 Model and preprocessors saved to model/ (both .keras and .h5 when possible)")

# =====================================================
# MODEL EVALUATION ON TEST SET
# =====================================================
# Evaluate model performance on held-out test data
# Test set has never been used during training or validation

# Make predictions on test set
y_true = np.argmax(y_test, axis=1)                    # Convert one-hot back to class indices
y_pred = np.argmax(model.predict(X_test), axis=1)    # Get predicted class indices

# Calculate overall test accuracy
# Accuracy = (correct predictions) / (total predictions)
test_acc = accuracy_score(y_true, y_pred)
print(f"\n🔎 Test accuracy: {test_acc:.4f}")

# Print detailed classification metrics per crop
# Includes precision, recall, and F1-score for each class
print("\nClassification report:\n")
print(classification_report(y_true, y_pred, target_names=crops))

# =====================================================
# VALIDATION ON CANONICAL MIDPOINTS
# =====================================================
# Test predictions on the original optimal soil conditions for each crop
# If model is well-trained, it should predict each crop when given that crop's optimal conditions

print("\n🌾 Predictions for canonical midpoints:")
for crop in crops:
    # Scale the canonical midpoint using the same scaler
    input_scaled = scaler.transform([soil_midpoints[crop]])
    # Get raw model output (probability distribution)
    pred = model.predict(input_scaled, verbose=0)
    # Convert probability distribution to crop name
    predicted_crop = encoder.inverse_transform([np.argmax(pred)])[0]
    print(f"{crop}: Predicted -> {predicted_crop}")

# =====================================================
# ANALYSIS ARTIFACTS: CORRELATION MATRIX, CONFUSION MATRIX, TRAINING CURVES
# =====================================================
# Generate comprehensive visualizations and reports for model analysis

os.makedirs("model/analysis", exist_ok=True)

# Feature names for labeling in DataFrames and plots
feature_names = ["N", "P", "K", "pH", "Moisture", "Temperature"]

# Use original (unscaled) X to compute correlations
# Correlations are scale-invariant, so we can use any version
df_features = pd.DataFrame(X, columns=feature_names)

# =====================================================
# CORRELATION MATRIX
# =====================================================
# Shows how strongly each pair of features are related (linear correlation)
# Values range from -1 (perfect negative correlation) to +1 (perfect positive correlation)
# Helps identify redundant features or relationships between soil properties

corr = df_features.corr()
corr_csv = "model/analysis/correlation_matrix.csv"
corr_img = "model/analysis/correlation_matrix.png"

# Save as CSV for tabular analysis
corr.to_csv(corr_csv)

# Create and save heatmap visualization
plt.figure(figsize=(8, 6))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm")
plt.title("Feature Correlation Matrix")
plt.tight_layout()
plt.savefig(corr_img, dpi=150)
plt.close()
print(f"Saved correlation matrix CSV -> {corr_csv} and image -> {corr_img}")

# =====================================================
# CONFUSION MATRIX
# =====================================================
# Shows how often each crop was confused with others in predictions
# Diagonal represents correct predictions; off-diagonal represents errors
# Helps identify which crop types the model struggles to distinguish

cm = confusion_matrix(y_true, y_pred)
cm_df = pd.DataFrame(cm, index=crops, columns=crops)
cm_csv = "model/analysis/confusion_matrix.csv"
cm_img = "model/analysis/confusion_matrix.png"

# Save as CSV
cm_df.to_csv(cm_csv)

# Create and save heatmap visualization
plt.figure(figsize=(8, 6))
sns.heatmap(cm_df, annot=True, fmt="d", cmap="Blues")
plt.ylabel("True")
plt.xlabel("Predicted")
plt.title("Confusion Matrix")
plt.tight_layout()
plt.savefig(cm_img, dpi=150)
plt.close()
print(f"Saved confusion matrix CSV -> {cm_csv} and image -> {cm_img}")

# =====================================================
# CLASSIFICATION REPORT & PERFORMANCE SUMMARY
# =====================================================
# Generate detailed per-class metrics and save as CSV and Markdown

# Get classification report as dictionary for flexible formatting
report_dict = classification_report(y_true, y_pred, target_names=crops, output_dict=True)
report_df = pd.DataFrame(report_dict).transpose()
report_csv = "model/analysis/classification_report.csv"
report_md = "model/analysis/performance_report.md"

# Save as CSV
report_df.to_csv(report_csv)
print(f"Saved classification report CSV -> {report_csv}")

# Create a lightweight markdown summary linking artifacts
# This provides a human-readable overview of model performance
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

# =====================================================
# TRAINING CURVES
# =====================================================
# Plot accuracy and loss over epochs to visualize training progression
# Useful for detecting overfitting (when validation curves diverge from training curves)

# Extract training history
acc = history.history.get("accuracy", [])       # Training accuracy per epoch
val_acc = history.history.get("val_accuracy", [])  # Validation accuracy per epoch
loss = history.history.get("loss", [])          # Training loss per epoch
val_loss = history.history.get("val_loss", [])  # Validation loss per epoch

curves_img = "model/analysis/accuracy_loss.png"

# Create side-by-side subplots for accuracy and loss
plt.figure(figsize=(12, 5))

# Left subplot: Accuracy over epochs
plt.subplot(1, 2, 1)
plt.plot(acc, label="train_acc")
plt.plot(val_acc, label="val_acc")
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.legend()
plt.title("Accuracy vs Epoch")

# Right subplot: Loss over epochs
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
