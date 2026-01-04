#!/usr/bin/env python3
"""Feature-engineering + hyperparameter search for RF and XGBoost.

Loads `datacore_prepared.csv` (falls back to `datacore.csv`), drops
`soil_type`/`fertilizer_name`, creates log/square/interaction features, then
runs RandomizedSearchCV for RandomForest and XGBoost (if available). Saves
models and analysis under `model_dataset_fe/analysis/`.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import PolynomialFeatures
import joblib
import matplotlib.pyplot as plt

try:
    import xgboost as xgb
    has_xgb = True
except Exception:
    has_xgb = False


OUTDIR = Path("model_dataset_fe/analysis")
OUTDIR.mkdir(parents=True, exist_ok=True)


def find_column(df, candidates):
    for cand in candidates:
        for name in df.columns:
            if cand.lower() == name.lower() or cand.lower() in name.lower():
                return name
    return None


def main():
    # load
    for p in (Path('datacore_prepared.csv'), Path('datacore.csv')):
        if p.exists():
            df = pd.read_csv(p)
            print('Loaded', p)
            break
    else:
        print('No dataset found. Exiting.')
        sys.exit(2)

    # drop unwanted categorical columns
    drop_cols = [c for c in df.columns if any(x in c.lower() for x in ('soil_type', 'fertilizer', 'fertiliser'))]
    if drop_cols:
        print('Dropping columns:', drop_cols)
        df = df.drop(columns=drop_cols)

    target_col = find_column(df, ['crop', 'crop_type', 'crop type'])
    if target_col is None:
        print('Target not found. Columns:', df.columns.tolist())
        sys.exit(3)

    # sensor mapping
    candidates = {
        'N': ['nitrogen', 'n'],
        'P': ['phosphorus', 'p', 'phosphorous'],
        'K': ['potassium', 'k'],
        'Temp': ['temperature', 'temp'],
        'Humidity': ['humidity', 'humid'],
        'Moisture': ['moisture', 'moist']
    }

    sensors = {}
    for k, cands in candidates.items():
        col = find_column(df, cands)
        if col:
            sensors[k] = col

    if not sensors:
        print('No sensor columns found. Exiting.')
        sys.exit(4)

    base_features = list(sensors.values())

    # basic feature engineering
    # log1p transform to reduce skew for numeric sensors
    for col in base_features:
        new = f'{col}_log1p'
        df[new] = np.log1p(df[col].fillna(0))

    # polynomial interactions (degree=2) on base features
    poly = PolynomialFeatures(degree=2, interaction_only=False, include_bias=False)
    poly_cols = [f'{c}_poly' for c in base_features]
    # we'll compute polynomial features via sklearn later in pipeline

    engineered = [f'{c}_log1p' for c in base_features]

    feature_cols = engineered  # start with log features

    X = df[feature_cols].copy()
    y = df[target_col].copy()

    mask = y.notna()
    X = X[mask]
    y = y[mask]

    # pipeline for numeric impute + scaling + polynomial
    numeric_transform = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('poly', PolynomialFeatures(degree=2, interaction_only=False, include_bias=False)),
        ('scaler', StandardScaler())
    ])

    # columns indices
    col_idx = list(range(X.shape[1]))

    # transform X
    X_trans = numeric_transform.fit_transform(X)

    # label encode y
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y_enc = le.fit_transform(y.astype(str))

    X_train, X_test, y_train, y_test = train_test_split(X_trans, y_enc, test_size=0.2, random_state=42, stratify=y_enc)

    results = {}

    # RandomForest randomized search
    rf = RandomForestClassifier(random_state=42, n_jobs=-1)
    param_dist_rf = {
        'n_estimators': [100, 200, 400],
        'max_depth': [None, 10, 20, 30],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'class_weight': [None, 'balanced']
    }

    rs_rf = RandomizedSearchCV(rf, param_dist_rf, n_iter=20, cv=3, scoring='accuracy', n_jobs=-1, random_state=42, verbose=1)
    print('Starting RandomizedSearchCV for RandomForest...')
    rs_rf.fit(X_train, y_train)
    best_rf = rs_rf.best_estimator_
    y_pred_rf = best_rf.predict(X_test)
    acc_rf = accuracy_score(y_test, y_pred_rf)
    print('Best RF acc:', acc_rf)
    results['rf'] = {'accuracy': float(acc_rf), 'best_params': rs_rf.best_params_}

    # save rf artifacts
    joblib.dump(best_rf, OUTDIR / 'rf_best.joblib')
    joblib.dump(numeric_transform, OUTDIR / 'numeric_transform.joblib')
    joblib.dump(le, OUTDIR / 'label_encoder.joblib')
    pd.DataFrame(classification_report(y_test, y_pred_rf, output_dict=True)).T.to_csv(OUTDIR / 'classification_report_rf.csv')
    with open(OUTDIR / 'summary_rf.json', 'w') as f:
        json.dump(results['rf'], f, indent=2)
    cm = confusion_matrix(y_test, y_pred_rf)
    plt.figure(figsize=(8, 6))
    plt.imshow(cm, cmap=plt.cm.Blues)
    plt.title('Confusion Matrix - RF (FE)')
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(OUTDIR / 'confusion_matrix_rf_fe.png')
    plt.close()

    # feature importances: map back to engineered/poly feature names if possible
    try:
        importances = best_rf.feature_importances_
        top_idx = np.argsort(importances)[::-1][:20]
        feat_names = []
        # build approximate feature names from polynomial output
        # use PolynomialFeatures to get feature names
        pf = PolynomialFeatures(degree=2, interaction_only=False, include_bias=False)
        pf.fit(X.iloc[:1, :])
        names = pf.get_feature_names_out([c for c in X.columns])
        for i in top_idx:
            feat_names.append((names[i] if i < len(names) else f'feat_{i}', float(importances[i])))
        pd.DataFrame(feat_names, columns=['feature', 'importance']).to_csv(OUTDIR / 'rf_top_feature_importances.csv', index=False)
    except Exception:
        pass

    # XGBoost search
    if has_xgb:
        print('Starting RandomizedSearchCV for XGBoost...')
        xgb_clf = xgb.XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', n_jobs=-1, random_state=42)
        param_dist_xgb = {
            'n_estimators': [100, 200, 400],
            'max_depth': [3, 6, 10],
            'learning_rate': [0.01, 0.05, 0.1],
            'subsample': [0.6, 0.8, 1.0],
            'colsample_bytree': [0.6, 0.8, 1.0]
        }
        rs_xgb = RandomizedSearchCV(xgb_clf, param_dist_xgb, n_iter=20, cv=3, scoring='accuracy', n_jobs=-1, random_state=42, verbose=1)
        rs_xgb.fit(X_train, y_train)
        best_xgb = rs_xgb.best_estimator_
        y_pred_xgb = best_xgb.predict(X_test)
        acc_xgb = accuracy_score(y_test, y_pred_xgb)
        print('Best XGB acc:', acc_xgb)
        results['xgb'] = {'accuracy': float(acc_xgb), 'best_params': rs_xgb.best_params_}
        joblib.dump(best_xgb, OUTDIR / 'xgb_best.joblib')
        pd.DataFrame(classification_report(y_test, y_pred_xgb, output_dict=True)).T.to_csv(OUTDIR / 'classification_report_xgb.csv')
        with open(OUTDIR / 'summary_xgb.json', 'w') as f:
            json.dump(results['xgb'], f, indent=2)
        cmx = confusion_matrix(y_test, y_pred_xgb)
        plt.figure(figsize=(8, 6))
        plt.imshow(cmx, cmap=plt.cm.Blues)
        plt.title('Confusion Matrix - XGB (FE)')
        plt.colorbar()
        plt.tight_layout()
        plt.savefig(OUTDIR / 'confusion_matrix_xgb_fe.png')
        plt.close()
    else:
        print('XGBoost not installed; skipped XGB search.')

    # overall results
    with open(OUTDIR / 'results_summary.json', 'w') as f:
        json.dump(results, f, indent=2)

    print('Feature-engineering + search complete. Artifacts in', OUTDIR)


if __name__ == '__main__':
    main()
