"""Binary grouping experiment: Cereals vs Others
Saves artifacts to model_dataset_binary/analysis
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
OUT = 'model_dataset_binary'
ANALYSIS = os.path.join(OUT, 'analysis')
os.makedirs(ANALYSIS, exist_ok=True)

print('Loading dataset...')
df = pd.read_csv(DATA)
cols = {c.lower(): c for c in df.columns}
N = cols.get('nitrogen')
P = cols.get('phosphorous') or cols.get('phosphorus')
K = cols.get('potassium')
TEMP = cols.get('temparature') or cols.get('temperature')
HUM = cols.get('humidity')
MOIST = cols.get('moisture')
CROP = cols.get('crop type') or cols.get('crop') or cols.get('label')
if any(v is None for v in [N,P,K,TEMP,HUM,MOIST,CROP]):
    raise RuntimeError('Missing expected columns')

# cereals list
cereals = set(['Wheat','Paddy','Maize','Barley','Millets'])

# prepare
features = [N,P,K,TEMP,HUM,MOIST]
X = df[features].apply(pd.to_numeric, errors='coerce')
y = df[CROP].astype(str).str.strip()

# map to binary label
y_bin = y.apply(lambda v: 'Cereals' if v in cereals else 'Others')
mask = X.notnull().all(axis=1) & y_bin.notnull()
X = X[mask]
y_bin = y_bin[mask]
print('Rows used:', len(X))

# features: zero indicators + ratios
for col in [N,P,K]:
    X[f'{col}_is_zero'] = (X[col]==0).astype(int)
X['N_over_P'] = X[N] / (X[P].replace(0, np.nan) + 1e-6)
X['N_over_K'] = X[N] / (X[K].replace(0, np.nan) + 1e-6)
X['P_over_K'] = X[P] / (X[K].replace(0, np.nan) + 1e-6)
X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(X.median())

# scale
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
joblib.dump(scaler, os.path.join(OUT, 'scaler.save'))

# encode
le = LabelEncoder()
y_enc = le.fit_transform(y_bin)
joblib.dump(le, os.path.join(OUT, 'label_encoder.save'))

# split
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_enc, test_size=0.2, stratify=y_enc, random_state=42)

# RF
from sklearn.ensemble import RandomForestClassifier
rf = RandomForestClassifier(n_estimators=300, class_weight='balanced', random_state=42, n_jobs=-1)
print('Training RF...')
rf.fit(X_train, y_train)
joblib.dump(rf, os.path.join(OUT, 'rf_binary.joblib'))

y_pred = rf.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print('RF accuracy:', acc)
print(classification_report(y_test, y_pred, target_names=list(le.classes_)))

cm = confusion_matrix(y_test, y_pred)
cm_df = pd.DataFrame(cm, index=le.classes_, columns=le.classes_)
cm_df.to_csv(os.path.join(ANALYSIS, 'confusion_binary.csv'))
plt.figure(figsize=(6,5))
sns.heatmap(cm_df, annot=True, fmt='d', cmap='Blues')
plt.title('Confusion Matrix Binary')
plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS, 'confusion_binary.png'), dpi=150)
plt.close()

# feature importances
fi = rf.feature_importances_
fi_df = pd.Series(fi, index=X.columns).sort_values(ascending=False)
fi_df.to_csv(os.path.join(ANALYSIS, 'feature_importances_binary.csv'))
plt.figure(figsize=(8,5))
fi_df.plot(kind='bar')
plt.title('Feature importances (binary RF)')
plt.tight_layout()
plt.savefig(os.path.join(ANALYSIS, 'feature_importances_binary.png'), dpi=150)
plt.close()

# Try XGBoost
try:
    from xgboost import XGBClassifier
    print('Training XGBoost...')
    xgb = XGBClassifier(use_label_encoder=False, eval_metric='logloss', n_estimators=200, random_state=42, n_jobs=-1)
    xgb.fit(X_train, y_train)
    joblib.dump(xgb, os.path.join(OUT, 'xgb_binary.joblib'))
    y_pred2 = xgb.predict(X_test)
    acc2 = accuracy_score(y_test, y_pred2)
    print('XGB accuracy:', acc2)
except Exception as e:
    print('XGBoost not available or failed:', e)

print('Done. Artifacts in', ANALYSIS)
