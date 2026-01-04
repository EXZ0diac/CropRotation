#!/usr/bin/env python3
"""Compute baseline accuracy and mutual information for trimmed dataset.

Writes `model_dataset_trimmed/analysis/signal_report.json` and
`model_dataset_trimmed/analysis/mutual_info.csv`.
"""
from pathlib import Path
import json
import sys

import pandas as pd
import numpy as np
from sklearn.feature_selection import mutual_info_classif
from sklearn.preprocessing import LabelEncoder


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

X = df[[c for c in df.columns if c != crop_col]].copy()
y = df[crop_col].astype(str).copy()

# drop rows with missing target
mask = y.notna()
X = X[mask]
y = y[mask]

# encode y
le = LabelEncoder()
y_enc = le.fit_transform(y)

# baseline: majority-class accuracy
counts = pd.Series(y).value_counts()
majority = float(counts.max() / counts.sum())

# mutual information (requires numeric input) - coerce columns to numeric where possible
X_num = X.copy()
for col in X_num.columns:
    X_num[col] = pd.to_numeric(X_num[col], errors='coerce')
# fill na with median
X_num = X_num.fillna(X_num.median())

mi = mutual_info_classif(X_num.values, y_enc, discrete_features=False, random_state=42)

mi_df = pd.DataFrame({'feature': X_num.columns, 'mutual_info': mi})
mi_df = mi_df.sort_values('mutual_info', ascending=False)
mi_df.to_csv(OUTDIR / 'mutual_info.csv', index=False)

report = {
    'rows': int(len(X_num)),
    'n_features': int(X_num.shape[1]),
    'n_classes': int(len(le.classes_)),
    'majority_class_accuracy': float(majority),
    'class_distribution': counts.to_dict(),
    'top_features': mi_df.head(5).to_dict(orient='records')
}

with open(OUTDIR / 'signal_report.json', 'w') as f:
    json.dump(report, f, indent=2)

print('Wrote signal_report.json and mutual_info.csv to', OUTDIR)
