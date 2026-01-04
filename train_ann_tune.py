#!/usr/bin/env python3
"""Randomized hyperparameter search for Keras ANN.

Reads `datacore_filtered_trimmed.csv`, runs N random trials over architecture
and training hyperparameters, saves a `ann_tune_results.csv` and the best
model to `model_dataset_trimmed/analysis/ann_tuned_model.keras`.
"""
import json
import random
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
except Exception:
    print('TensorFlow required for tuning. Install tensorflow.')
    sys.exit(1)


OUTDIR = Path('model_dataset_trimmed/analysis')
OUTDIR.mkdir(parents=True, exist_ok=True)

SRC = Path('datacore_filtered_trimmed.csv')
if not SRC.exists():
    print('Run create_trimmed_csv.py first to create', SRC)
    sys.exit(1)

df = pd.read_csv(SRC)

# find crop column
crop_col = None
for c in df.columns:
    if 'crop' in c.lower():
        crop_col = c
        break
if crop_col is None:
    print('Crop column not found in', SRC)
    sys.exit(1)

# features = all columns except crop
X = df[[c for c in df.columns if c != crop_col]].copy()
y = df[crop_col].copy()

# drop missing target
mask = y.notna()
X = X[mask]
y = y[mask]

imp = SimpleImputer(strategy='median')
X_imp = imp.fit_transform(X)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imp)

le = LabelEncoder()
y_enc = le.fit_transform(y.astype(str))

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_enc, test_size=0.2, random_state=42, stratify=y_enc)

num_classes = len(le.classes_)
try:
    y_train_cat = tf.keras.utils.to_categorical(y_train, num_classes)
    y_test_cat = tf.keras.utils.to_categorical(y_test, num_classes)
except Exception:
    print('Error converting labels to categorical')
    sys.exit(1)

def build_model(input_dim, config):
    model = Sequential()
    model.add(Dense(config['layer1'], activation='relu', input_shape=(input_dim,)))
    if config['dropout1'] > 0:
        model.add(Dropout(config['dropout1']))
    if config['layer2'] > 0:
        model.add(Dense(config['layer2'], activation='relu'))
        if config['dropout2'] > 0:
            model.add(Dropout(config['dropout2']))
    if config['layer3'] > 0:
        model.add(Dense(config['layer3'], activation='relu'))
    model.add(Dense(num_classes, activation='softmax'))
    opt = tf.keras.optimizers.Adam(learning_rate=config['lr'])
    model.compile(optimizer=opt, loss='categorical_crossentropy', metrics=['accuracy'])
    return model


# hyperparameter search space
space = {
    'layer1': [64, 128, 256],
    'layer2': [0, 32, 64],
    'layer3': [0, 16, 32],
    'dropout1': [0.0, 0.2, 0.3],
    'dropout2': [0.0, 0.1, 0.2],
    'lr': [1e-3, 5e-4, 1e-4],
    'batch_size': [32, 64, 128]
}

def sample_config():
    return {k: random.choice(v) for k, v in space.items()}

TRIALS = 12
results = []
best_acc = -1.0
best_cfg = None
best_model_path = OUTDIR / 'ann_tuned_model.keras'

for t in range(TRIALS):
    cfg = sample_config()
    print(f'Trial {t+1}/{TRIALS}:', cfg)
    model = build_model(X_train.shape[1], cfg)
    ckpt = ModelCheckpoint(str(OUTDIR / f'ann_tune_trial_{t+1}.keras'), monitor='val_loss', save_best_only=True)
    es = EarlyStopping(monitor='val_loss', patience=6, restore_best_weights=True)
    hist = model.fit(X_train, y_train_cat, validation_split=0.15, epochs=60, batch_size=cfg['batch_size'], callbacks=[ckpt, es], verbose=0)
    # evaluate on test
    test_loss, test_acc = model.evaluate(X_test, y_test_cat, verbose=0)
    print(f'  test_acc={test_acc:.4f}')
    results.append({'trial': t+1, 'config': cfg, 'test_acc': float(test_acc)})
    # save best
    if test_acc > best_acc:
        best_acc = test_acc
        best_cfg = cfg
        # save model
        model.save(best_model_path)

# save results
res_df = pd.DataFrame([{'trial': r['trial'], **r['config'], 'test_acc': r['test_acc']} for r in results])
res_df.to_csv(OUTDIR / 'ann_tune_results.csv', index=False)
with open(OUTDIR / 'ann_tune_summary.json', 'w') as f:
    json.dump({'best_acc': float(best_acc), 'best_cfg': best_cfg, 'num_trials': TRIALS}, f, indent=2)

# save preprocessing artifacts
joblib.dump(imp, OUTDIR / 'imputer.joblib')
joblib.dump(scaler, OUTDIR / 'scaler.joblib')
joblib.dump(le, OUTDIR / 'label_encoder.joblib')

print('Tuning complete. Best acc=', best_acc)
print('Artifacts in', OUTDIR)
