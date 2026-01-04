"""Grouping experiment
- Map original crop labels into broader groups
- Train RandomForest (and XGBoost if installed)
- Save metrics and plots to model_dataset_grouped/analysis
"""
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

DATA = 'datacore.csv'
OUT = 'model_dataset_grouped'
ANALYSIS = os.path.join(OUT, 'analysis')
os.makedirs(ANALYSIS, exist_ok=True)

print('Loading dataset...')
df = pd.read_csv(DATA)
print('Columns:', list(df.columns))

# normalize columns
cols = {c.lower(): c for c in df.columns}
N = cols.get('nitrogen')
P = cols.get('phosphorous') or cols.get('phosphorus')
K = cols.get('potassium')
TEMP = cols.get('temparature') or cols.get('temperature')
HUM = cols.get('humidity')
MOIST = cols.get('moisture')
CROP = cols.get('crop type') or cols.get('crop') or cols.get('label')
if any(v is None for v in [N,P,K,TEMP,HUM,MOIST,CROP]):
    raise RuntimeError('Missing expected columns: ' + str([c for c in [N,P,K,TEMP,HUM,MOIST,CROP] if c is None]))

# mapping: group to fewer classes
mapping = {
    'Wheat':'Cereals','Paddy':'Cereals','Maize':'Cereals','Barley':'Cereals','Millets':'Cereals',
    'Pulses':'Pulses','Ground Nuts':'Pulses',
    'Cotton':'Cash_Oil','Tobacco':'Cash_Oil','Oil seeds':'Cash_Oil',
    'Sugarcane':'Sugarcane'
}

# prepare data
features = [N,P,K,TEMP,HUM,MOIST]
X = df[features].apply(pd.to_numeric, errors='coerce')
y = df[CROP].astype(str).str.strip()
# map labels
y_mapped = y.map(mapping)
mask = X.notnull().all(axis=1) & y_mapped.notnull()
X = X[mask]
y_mapped = y_mapped[mask]
print('Using rows:', len(X))

# add zero-indicator features
for col in [N,P,K]:
    X[f'{col}_is_zero'] = (X[col]==0).astype(int)
# ratios
X['N_over_P'] = X[N] / (X[P].replace(0, np.nan) + 1e-6)
X['N_over_K'] = X[N] / (X[K].replace(0, np.nan) + 1e-6)
X['P_over_K'] = X[P] / (X[K].replace(0, np.nan) + 1e-6)
# fill inf/nan
X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(X.median())

# scale
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
joblib.dump(scaler, os.path.join(OUT, 'scaler.save'))

# encode
le = LabelEncoder()
y_enc = le.fit_transform(y_mapped)
joblib.dump(le, os.path.join(OUT, 'label_encoder.save'))

# split
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_enc, test_size=0.2, stratify=y_enc, random_state=42)

# RandomForest
rf = RandomForestClassifier(n_estimators=300, class_weight='balanced', random_state=42, n_jobs=-1)
print('Training RandomForest...')
rf.fit(X_train, y_train)
joblib.dump(rf, os.path.join(OUT, 'rf_grouped.joblib'))

y_pred = rf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print('RF accuracy:', acc)
print(classification_report(y_test, y_pred, target_names=list(le.classes_)))

# confusion matrix
cm = confusion_matrix(y_test, y_pred)
cm_df = pd.DataFrame(cm, index=le.classes_, columns=le.classes_)
cm_df.to_csv(os.path.join(ANALYSIS, 'confusion_matrix_grouped.csv'))
plt.figure(figsize=(8,6))
sns.heatmap(cm_df, annot=True, fmt='d', cmap='Blues')
plt.title('Confusion Matrix (Grouped)')
plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS, 'confusion_matrix_grouped.png'), dpi=150)
plt.close()

# feature importances
fi = rf.feature_importances_
fi_df = pd.Series(fi, index=X.columns).sort_values(ascending=False)
fi_df.to_csv(os.path.join(ANALYSIS, 'feature_importances_grouped.csv'))
plt.figure(figsize=(10,6))
fi_df.plot(kind='bar')
plt.title('Feature importances (RF grouped)')
plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS, 'feature_importances_grouped.png'), dpi=150)
plt.close()

# save summary
with open(os.path.join(ANALYSIS, 'grouping_summary.txt'), 'w') as f:
    f.write(f'RF accuracy: {acc}\n')
    f.write('Classes: ' + ','.join(list(le.classes_)) + '\n')

# Try XGBoost if available
try:
    from xgboost import XGBClassifier
    print('Training XGBoost...')
    xgb = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', n_estimators=200, random_state=42, n_jobs=-1)
    xgb.fit(X_train, y_train)
    joblib.dump(xgb, os.path.join(OUT, 'xgb_grouped.joblib'))
    y_pred2 = xgb.predict(X_test)
    acc2 = accuracy_score(y_test, y_pred2)
    print('XGB accuracy:', acc2)
    with open(os.path.join(ANALYSIS, 'grouping_summary.txt'), 'a') as f:
        f.write(f'XGB accuracy: {acc2}\n')
except Exception as e:
    print('XGBoost not available or failed:', e)

print('Done. Artifacts in', ANALYSIS)
