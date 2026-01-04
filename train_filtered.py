#!/usr/bin/env python3
"""Train models after removing specified crop classes.

Filters out user-specified crop classes and trains RandomForest and XGBoost
(if installed). Writes analysis into `model_dataset_filtered/analysis/`.
"""
import sys
from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import matplotlib.pyplot as plt

try:
    import xgboost as xgb
    has_xgb = True
except Exception:
    has_xgb = False


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
        df = df.drop(columns=drop_cols)

    target_col = find_column(df, ['crop', 'crop_type', 'crop type'])
    if target_col is None:
        print('Target not found. Columns:', df.columns.tolist())
        sys.exit(3)

    # filter out rows with target in REMOVALS
    mask_keep = ~df[target_col].astype(str).str.strip().str.lower().isin([r.lower() for r in REMOVALS])
    before = len(df)
    df = df[mask_keep]
    after = len(df)
    print(f'Removed {before-after} rows; {after} rows remain')

    # find sensor columns
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
        for name in df.columns:
            if any(c.lower() in name.lower() for c in cands):
                sensors[key] = name
                break

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

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_enc, test_size=0.2, random_state=42, stratify=y_enc)

    rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    acc_rf = accuracy_score(y_test, y_pred_rf)
    print(f'RandomForest accuracy: {acc_rf:.4f}')
    joblib.dump(rf, OUTDIR / 'rf_model.joblib')
    pd.DataFrame(classification_report(y_test, y_pred_rf, output_dict=True)).T.to_csv(OUTDIR / 'classification_report_rf.csv')
    with open(OUTDIR / 'summary_rf.json', 'w') as f:
        json.dump({'accuracy': acc_rf, 'n_classes': int(len(le.classes_))}, f, indent=2)
    cm = confusion_matrix(y_test, y_pred_rf)
    plt.figure(figsize=(8,6))
    plt.imshow(cm, cmap=plt.cm.Blues)
    plt.title('Confusion Matrix - RF (filtered)')
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(OUTDIR / 'confusion_matrix_rf.png')
    plt.close()

    if has_xgb:
        xgb_clf = xgb.XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', n_estimators=200, random_state=42)
        xgb_clf.fit(X_train, y_train)
        y_pred_xgb = xgb_clf.predict(X_test)
        acc_xgb = accuracy_score(y_test, y_pred_xgb)
        print(f'XGBoost accuracy: {acc_xgb:.4f}')
        joblib.dump(xgb_clf, OUTDIR / 'xgb_model.joblib')
        pd.DataFrame(classification_report(y_test, y_pred_xgb, output_dict=True)).T.to_csv(OUTDIR / 'classification_report_xgb.csv')
        with open(OUTDIR / 'summary_xgb.json', 'w') as f:
            json.dump({'accuracy': acc_xgb, 'n_classes': int(len(le.classes_))}, f, indent=2)
        cmx = confusion_matrix(y_test, y_pred_xgb)
        plt.figure(figsize=(8,6))
        plt.imshow(cmx, cmap=plt.cm.Blues)
        plt.title('Confusion Matrix - XGB (filtered)')
        plt.colorbar()
        plt.tight_layout()
        plt.savefig(OUTDIR / 'confusion_matrix_xgb.png')
        plt.close()
    else:
        print('XGBoost not installed; skipped XGB')

    # save preprocessing artifacts
    joblib.dump(imp, OUTDIR / 'imputer.joblib')
    joblib.dump(scaler, OUTDIR / 'scaler.joblib')
    joblib.dump(le, OUTDIR / 'label_encoder.joblib')

    print('Artifacts written to', OUTDIR)


if __name__ == '__main__':
    main()
