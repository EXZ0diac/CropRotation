#!/usr/bin/env python3
"""Train an ANN using only the trimmed CSV columns.

Loads `datacore_filtered_trimmed.csv`, trains a Keras ANN, and saves
artifacts under `model_dataset_trimmed/analysis/`.
"""
from pathlib import Path
import sys
import json

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import matplotlib.pyplot as plt

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
except Exception:
    print('TensorFlow not found; install tensorflow to run ANN training')
    tf = None


OUTDIR = Path('model_dataset_trimmed/analysis')
OUTDIR.mkdir(parents=True, exist_ok=True)


def main():
    src = None
    for p in (Path('datacore_filtered_trimmed.csv'), Path('datacore_filtered.csv')):
        if p.exists():
            src = p
            break
    if src is None:
        print('No trimmed CSV found. Run create_trimmed_csv.py first.')
        sys.exit(1)

    df = pd.read_csv(src)
    print('Loaded', src)

    # expected columns
    # try to find columns by name/substring
    def find(df, candidates):
        for cand in candidates:
            for col in df.columns:
                if cand.lower() == col.lower() or cand.lower() in col.lower() or col.lower() in cand.lower():
                    return col
        return None

    col_n = find(df, ['nitrogen', 'n'])
    col_p = find(df, ['phosphorus', 'p'])
    col_k = find(df, ['potassium', 'k'])
    col_temp = find(df, ['temperature', 'temp'])
    col_hum = find(df, ['humidity', 'humid'])
    col_moist = find(df, ['moisture', 'moist'])
    col_crop = find(df, ['crop', 'crop_type'])
    col_ph = find(df, ['ph'])

    cols = [col for col in [col_n, col_p, col_k, col_temp, col_hum, col_moist, col_ph, col_crop] if col is not None]
    if not col_crop:
        print('Crop column not found. Available columns:', df.columns.tolist())
        sys.exit(2)

    # ensure crop is last column for convenience
    feature_cols = [c for c in cols if c != col_crop]

    X = df[feature_cols].copy()
    y = df[col_crop].copy()

    # drop rows with missing target
    mask = y.notna()
    X = X[mask]
    y = y[mask]

    # impute and scale
    imp = SimpleImputer(strategy='median')
    X_imp = imp.fit_transform(X)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imp)

    le = LabelEncoder()
    y_enc = le.fit_transform(y.astype(str))

    num_classes = len(le.classes_)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_enc, test_size=0.2, random_state=42, stratify=y_enc)

    # to categorical
    try:
        y_train_cat = tf.keras.utils.to_categorical(y_train, num_classes)
        y_test_cat = tf.keras.utils.to_categorical(y_test, num_classes)
    except Exception:
        print('TensorFlow not available or error converting labels; aborting ANN training.')
        sys.exit(3)

    # build model
    input_dim = X_train.shape[1]
    model = Sequential([
        Dense(128, activation='relu', input_shape=(input_dim,)),
        Dropout(0.3),
        Dense(64, activation='relu'),
        Dropout(0.2),
        Dense(max(32, num_classes * 2), activation='relu'),
        Dense(num_classes, activation='softmax')
    ])

    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

    ckpt = ModelCheckpoint(str(OUTDIR / 'ann_trimmed_model.keras'), monitor='val_loss', save_best_only=True)
    es = EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True)

    history = model.fit(X_train, y_train_cat, validation_split=0.15, epochs=80, batch_size=32, callbacks=[ckpt, es], verbose=2)

    # evaluate
    test_loss, test_acc = model.evaluate(X_test, y_test_cat, verbose=0)
    print('ANN (trimmed) test accuracy:', test_acc)

    y_pred_prob = model.predict(X_test)
    y_pred = y_pred_prob.argmax(axis=1)

    pd.DataFrame(classification_report(y_test, y_pred, output_dict=True)).T.to_csv(OUTDIR / 'classification_report_ann_trimmed.csv')
    with open(OUTDIR / 'summary_ann_trimmed.json', 'w') as f:
        json.dump({'accuracy': float(test_acc), 'num_classes': int(num_classes)}, f, indent=2)

    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('Confusion Matrix - ANN (trimmed)')
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(OUTDIR / 'confusion_matrix_ann_trimmed.png')
    plt.close()

    # save artifacts
    joblib.dump(imp, OUTDIR / 'imputer.joblib')
    joblib.dump(scaler, OUTDIR / 'scaler.joblib')
    joblib.dump(le, OUTDIR / 'label_encoder.joblib')
    hist_df = pd.DataFrame(history.history)
    hist_df.to_csv(OUTDIR / 'ann_trimmed_history.csv', index=False)

    print('Finished. Artifacts in', OUTDIR)


if __name__ == '__main__':
    main()
