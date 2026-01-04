#!/usr/bin/env python3
"""
train_on_prepared.py

Run the improved RandomForest pipeline on `datacore_prepared.csv` produced by `prepare_datacore.py`.
This is a thin copy of `model_training_dataset_improved.py` but points to the prepared CSV.
"""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import json

DATA_PATH = "datacore_prepared.csv"
OUT_DIR = "model_dataset_improved_prepared"
ANALYSIS_DIR = os.path.join(OUT_DIR, "analysis")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(DATA_PATH)

print("Loading dataset...", DATA_PATH)
df = pd.read_csv(DATA_PATH)
print(df.columns.tolist())

# Expected columns (case-insensitive)
cols = {c.lower(): c for c in df.columns}
# map
col_N = cols.get('nitrogen') or cols.get('n')
col_K = cols.get('potassium') or cols.get('k')
col_P = cols.get('phosphorous') or cols.get('phosphorus') or cols.get('p')
col_temp = cols.get('temparature') or cols.get('temperature')
col_hum = cols.get('humidity')
col_moist = cols.get('moisture')
col_crop = cols.get('crop type') or cols.get('crop') or cols.get('label')

missing = [name for name, val in [('N', col_N), ('K', col_K), ('P', col_P), ('Temperature', col_temp), ('Humidity', col_hum), ('Moisture', col_moist), ('Crop', col_crop)] if val is None]
if missing:
    raise RuntimeError(f"Missing columns: {missing}. CSV columns: {list(df.columns)}")

# Use proper column names
feature_cols = [col_N, col_P, col_K, col_temp, col_hum, col_moist]
X = df[feature_cols].copy()
y = df[col_crop].astype(str).copy()

# Treat zeros in N/P/K as NaN
for c in [col_N, col_P, col_K]:
    X[c] = pd.to_numeric(X[c], errors='coerce')
    X[c] = X[c].replace(0, np.nan)

print("Missing values per column before imputation:\n", X.isna().sum())

# Impute median per column
imp = SimpleImputer(strategy='median')
X_imp = pd.DataFrame(imp.fit_transform(X), columns=X.columns)

# Feature engineering: ratios
X_imp['N_over_P'] = X_imp[col_N] / (X_imp[col_P].replace(0, np.nan) + 1e-6)
X_imp['N_over_K'] = X_imp[col_N] / (X_imp[col_K].replace(0, np.nan) + 1e-6)
X_imp['P_over_K'] = X_imp[col_P] / (X_imp[col_K].replace(0, np.nan) + 1e-6)

X_imp = X_imp.replace([np.inf, -np.inf], np.nan)
imp2 = SimpleImputer(strategy='median')
X_imp = pd.DataFrame(imp2.fit_transform(X_imp), columns=X_imp.columns)

# Scale
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imp)
joblib.dump(scaler, os.path.join(OUT_DIR, 'scaler.save'))

# Encode labels
le = LabelEncoder()
y_enc = le.fit_transform(y)
joblib.dump(le, os.path.join(OUT_DIR, 'label_encoder.save'))

# Split
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_enc, test_size=0.2, stratify=y_enc, random_state=42)

# Train RF
rf = RandomForestClassifier(n_estimators=200, class_weight='balanced', random_state=42, n_jobs=-1)
print("Training RandomForest...")
rf.fit(X_train, y_train)
joblib.dump(rf, os.path.join(OUT_DIR, 'rf_model.joblib'))

# Evaluate
y_pred = rf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"RandomForest test accuracy: {acc:.4f}")
print(classification_report(y_test, y_pred, target_names=list(le.classes_)))

cm = confusion_matrix(y_test, y_pred)
cm_df = pd.DataFrame(cm, index=le.classes_, columns=le.classes_)
cm_df.to_csv(os.path.join(ANALYSIS_DIR, 'confusion_matrix.csv'))
plt.figure(figsize=(10,8))
sns.heatmap(cm_df, annot=True, fmt='d', cmap='Blues')
plt.title('Confusion Matrix')
plt.ylabel('True')
plt.xlabel('Predicted')
plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS_DIR, 'confusion_matrix_rf.png'), dpi=150)
plt.close()

from sklearn.metrics import precision_recall_fscore_support
prec, rec, f1, sup = precision_recall_fscore_support(y_test, y_pred, labels=range(len(le.classes_)))
report_df = pd.DataFrame({'precision': prec, 'recall': rec, 'f1-score': f1, 'support': sup}, index=le.classes_)
report_df.to_csv(os.path.join(ANALYSIS_DIR, 'classification_report_rf.csv'))

with open(os.path.join(ANALYSIS_DIR, 'summary.json'), 'w') as fh:
    json.dump({'accuracy': acc, 'n_classes': len(le.classes_), 'classes': list(le.classes_)}, fh, indent=2)

fi = rf.feature_importances_
fi_df = pd.Series(fi, index=X_imp.columns).sort_values(ascending=False)
plt.figure(figsize=(8,6))
fi_df.plot(kind='bar')
plt.title('RandomForest feature importances')
plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS_DIR, 'feature_importances_rf.png'), dpi=150)
plt.close()

print('Saved RF analysis to', ANALYSIS_DIR)
print('Done.')
