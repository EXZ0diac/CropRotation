#!/usr/bin/env python3
"""Train an ANN on the filtered dataset (drop specified crops).

Loads `datacore_prepared.csv` (fallback `datacore.csv`), removes crops
`Oil seeds`, `pulses`, `tobacco`, `Cotton`, drops `soil_type`/`fertilizer_name`,
uses sensor numeric features + simple ratios, trains a Keras ANN with
early-stopping, and saves model + artifacts under
`model_dataset_filtered/analysis/`.
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
    print('TensorFlow not available in this environment. Install tensorflow to run ANN training.')
    tf = None


OUTDIR = Path('model_dataset_filtered/analysis')
OUTDIR.mkdir(parents=True, exist_ok=True)

REMOVALS = ['oil seeds', 'pulses', 'tobacco', 'cotton']


def find_column(df, candidates):
    for cand in candidates:
        for name in df.columns:
            if cand.lower() == name.lower() or cand.lower() in name.lower():
                return name
    return None


def main():
    for p in (Path('datacore_prepared.csv'), Path('datacore.csv')):
        if p.exists():
            df = pd.read_csv(p)
            print('Loaded', p)
            break
    else:
        print('No dataset found. Exiting.')
        sys.exit(2)

    # drop categorical columns the user doesn't want used
    drop_cols = [c for c in df.columns if any(x in c.lower() for x in ('soil_type', 'fertilizer', 'fertiliser'))]
    if drop_cols:
        print('Dropping columns:', drop_cols)
        df = df.drop(columns=drop_cols)

    target_col = find_column(df, ['crop', 'crop_type', 'crop type'])
    if target_col is None:
        print('Target not found. Columns:', df.columns.tolist())
        sys.exit(3)

    # filter out specified crops
    mask_keep = ~df[target_col].astype(str).str.strip().str.lower().isin([r.lower() for r in REMOVALS])
    before = len(df)
    df = df[mask_keep]
    after = len(df)
    print(f'Removed {before-after} rows; {after} rows remain')

    # sensor mapping
    col_map = {
        'nitrogen': ['nitrogen', 'n'],
        'phosphorus': ['phosphorus', 'phosphorous', 'p'],
        'potassium': ['potassium', 'k'],
        'temperature': ['temperature', 'temp'],
        'humidity': ['humidity', 'humid'],
        'moisture': ['moisture', 'moist']
    }
    sensors = {}
    for key, cands in col_map.items():
        found = find_column(df, cands)
        if found:
            sensors[key] = found

    if not sensors:
        print('No sensor columns found. Exiting.')
        sys.exit(4)

    feature_cols = list(sensors.values())

    # engineered ratios
    def safe_div(a, b):
        return np.where(b == 0, 0.0, a / b)

    if 'nitrogen' in sensors and 'phosphorus' in sensors:
        df['n_p_ratio'] = safe_div(df[sensors['nitrogen']].fillna(0), df[sensors['phosphorus']].fillna(0))
        feature_cols.append('n_p_ratio')
    if 'nitrogen' in sensors and 'potassium' in sensors:
        df['n_k_ratio'] = safe_div(df[sensors['nitrogen']].fillna(0), df[sensors['potassium']].fillna(0))
        feature_cols.append('n_k_ratio')
    if 'phosphorus' in sensors and 'potassium' in sensors:
        df['p_k_ratio'] = safe_div(df[sensors['phosphorus']].fillna(0), df[sensors['potassium']].fillna(0))
        feature_cols.append('p_k_ratio')

    X = df[feature_cols].copy()
    y = df[target_col].copy()

    mask = y.notna()
    X = X[mask]
    y = y[mask]

    imp = SimpleImputer(strategy='median')
    X_imp = imp.fit_transform(X)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imp)

    le = LabelEncoder()
    y_enc = le.fit_transform(y.astype(str))

    # train/test split
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_enc, test_size=0.2, random_state=42, stratify=y_enc)

    # one-hot for Keras
    num_classes = len(le.classes_)
    try:
        y_train_cat = tf.keras.utils.to_categorical(y_train, num_classes)
        y_test_cat = tf.keras.utils.to_categorical(y_test, num_classes)
    except Exception:
        print('TensorFlow not available or error converting labels; aborting ANN training.')
        sys.exit(5)

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

    # callbacks
    ckpt = ModelCheckpoint(str(OUTDIR / 'ann_model.keras'), monitor='val_loss', save_best_only=True)
    es = EarlyStopping(monitor='val_loss', patience=8, restore_best_weights=True)

    history = model.fit(X_train, y_train_cat, validation_split=0.15, epochs=100, batch_size=32, callbacks=[ckpt, es], verbose=2)

    # evaluate on test
    test_loss, test_acc = model.evaluate(X_test, y_test_cat, verbose=0)
    print(f'ANN test accuracy: {test_acc:.4f}')

    # predict and save reports
    y_pred_prob = model.predict(X_test)
    y_pred = y_pred_prob.argmax(axis=1)
    acc = accuracy_score(y_test, y_pred)

    report = classification_report(y_test, y_pred, output_dict=True)
    pd.DataFrame(report).T.to_csv(OUTDIR / 'classification_report_ann.csv')
    with open(OUTDIR / 'summary_ann.json', 'w') as f:
        json.dump({'accuracy': float(acc), 'num_classes': int(num_classes)}, f, indent=2)

    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('Confusion Matrix - ANN (filtered)')
    plt.colorbar()
    plt.tight_layout()
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.savefig(OUTDIR / 'confusion_matrix_ann.png')
    plt.close()

    # save preprocessing artifacts and label encoder
    joblib.dump(imp, OUTDIR / 'imputer.joblib')
    joblib.dump(scaler, OUTDIR / 'scaler.joblib')
    joblib.dump(le, OUTDIR / 'label_encoder.joblib')

    # save training history
    hist_df = pd.DataFrame(history.history)
    hist_df.to_csv(OUTDIR / 'ann_training_history.csv', index=False)

    print('ANN training complete. Artifacts in', OUTDIR)


if __name__ == '__main__':
    main()
