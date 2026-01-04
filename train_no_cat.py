#!/usr/bin/env python3
"""Train RF and XGBoost excluding soil_type and fertilizer_name.

Loads `datacore_prepared.csv` (falls back to `datacore.csv`), selects sensor numeric
features (N, P, K, Temperature, Humidity, Moisture), engineers simple ratios,
trains RandomForest and XGBoost (if available), and writes analysis under
`model_dataset_no_cat/analysis/`.
"""
import os
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import joblib
import matplotlib.pyplot as plt

try:
    import xgboost as xgb
    has_xgb = True
except Exception:
    has_xgb = False


OUTDIR = Path("model_dataset_no_cat/analysis")
OUTDIR.mkdir(parents=True, exist_ok=True)


def find_column(df, candidates):
    lc = {c.lower(): c for c in df.columns}
    for cand in candidates:
        for name in df.columns:
            if cand.lower() == name.lower() or cand.lower() in name.lower():
                return name
    return None


def main():
    # load data
    for p in (Path("datacore_prepared.csv"), Path("datacore.csv")):
        if p.exists():
            df = pd.read_csv(p)
            print(f"Loaded {p}")
            break
    else:
        print("No prepared or raw datacore CSV found. Exiting.")
        sys.exit(2)

    # drop explicit categorical columns user requested to ignore
    drop_cols = [c for c in df.columns if any(x in c.lower() for x in ("soil_type", "fertilizer", "fertiliser"))]
    if drop_cols:
        print(f"Dropping columns: {drop_cols}")
        df = df.drop(columns=drop_cols)

    # identify target column
    target_col = find_column(df, ["crop", "crop_type", "crop type"])
    if target_col is None:
        print("Could not find target column (crop). Available columns:\n", df.columns.tolist())
        sys.exit(3)

    # identify sensor numeric columns
    col_map = {
        'nitrogen': ['nitrogen', 'n', 'nitrogen (n)', 'nitrogen_ppm'],
        'phosphorus': ['phosphorus', 'phosphorous', 'p', 'phosphorus (p)'],
        'potassium': ['potassium', 'k', 'potassium (k)'],
        'temperature': ['temperature', 'temp'],
        'humidity': ['humidity', 'humid'],
        'moisture': ['moisture', 'moist']
    }

    sensors = {}
    for key, cands in col_map.items():
        found = find_column(df, cands)
        if found:
            sensors[key] = found

    if len(sensors) < 4:
        print("Warning: fewer than 4 sensor columns found. Found:", sensors)

    feature_cols = list(sensors.values())

    # create engineered ratio columns where possible
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

    # keep only selected features + target
    X = df[feature_cols].copy()
    y = df[target_col].copy()

    # basic cleaning: drop rows where y is missing
    mask = y.notna()
    X = X[mask]
    y = y[mask]

    # impute numeric
    imp = SimpleImputer(strategy='median')
    X_imp = imp.fit_transform(X)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imp)

    le = LabelEncoder()
    y_enc = le.fit_transform(y.astype(str))

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_enc, test_size=0.2, random_state=42, stratify=y_enc)

    # RandomForest
    rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    acc_rf = accuracy_score(y_test, y_pred_rf)
    print(f"RandomForest test accuracy: {acc_rf:.4f}")

    # save rf artifacts
    joblib.dump(rf, OUTDIR / 'rf_model.joblib')
    joblib.dump(imp, OUTDIR / 'imputer.joblib')
    joblib.dump(scaler, OUTDIR / 'scaler.joblib')
    joblib.dump(le, OUTDIR / 'label_encoder.joblib')

    report = classification_report(y_test, y_pred_rf, output_dict=True)
    report_df = pd.DataFrame(report).T
    report_df.to_csv(OUTDIR / 'classification_report_rf.csv')
    with open(OUTDIR / 'summary_rf.json', 'w') as f:
        json.dump({'accuracy': acc_rf, 'n_classes': int(len(le.classes_))}, f, indent=2)

    cm = confusion_matrix(y_test, y_pred_rf)
    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('Confusion Matrix - RandomForest')
    plt.colorbar()
    plt.tight_layout()
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.savefig(OUTDIR / 'confusion_matrix_rf.png')
    plt.close()

    # XGBoost (optional)
    if has_xgb:
        print('Training XGBoost...')
        xgb_clf = xgb.XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', n_estimators=200, random_state=42)
        xgb_clf.fit(X_train, y_train)
        y_pred_xgb = xgb_clf.predict(X_test)
        acc_xgb = accuracy_score(y_test, y_pred_xgb)
        print(f"XGBoost test accuracy: {acc_xgb:.4f}")
        joblib.dump(xgb_clf, OUTDIR / 'xgb_model.joblib')
        report_xgb = classification_report(y_test, y_pred_xgb, output_dict=True)
        pd.DataFrame(report_xgb).T.to_csv(OUTDIR / 'classification_report_xgb.csv')
        with open(OUTDIR / 'summary_xgb.json', 'w') as f:
            json.dump({'accuracy': acc_xgb, 'n_classes': int(len(le.classes_))}, f, indent=2)
        cmx = confusion_matrix(y_test, y_pred_xgb)
        plt.figure(figsize=(8, 6))
        plt.imshow(cmx, interpolation='nearest', cmap=plt.cm.Blues)
        plt.title('Confusion Matrix - XGBoost')
        plt.colorbar()
        plt.tight_layout()
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.savefig(OUTDIR / 'confusion_matrix_xgb.png')
        plt.close()
    else:
        print('XGBoost not installed; skipped.')

    print('Artifacts written to', OUTDIR)


if __name__ == '__main__':
    main()
