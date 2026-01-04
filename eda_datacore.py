"""EDA for datacore.csv
Generates:
 - per-class mean/std CSV
 - mutual information ranking CSV
 - boxplot per feature (PNG)
 - pairplot for top 3 features (PNG)
 - summary markdown
All outputs saved to model_dataset_improved/analysis/
"""
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_selection import mutual_info_classif

DATA_PATH = 'datacore.csv'
OUT = 'model_dataset_improved/analysis'
os.makedirs(OUT, exist_ok=True)

print('Loading', DATA_PATH)
df = pd.read_csv(DATA_PATH)
print('Columns:', list(df.columns))

# normalize column names
cols_map = {c.lower(): c for c in df.columns}
# expected names
n_col = cols_map.get('nitrogen', cols_map.get('n'))
p_col = cols_map.get('phosphorous', cols_map.get('phosphorus', cols_map.get('p')))
k_col = cols_map.get('potassium', cols_map.get('k'))
t_col = cols_map.get('temparature', cols_map.get('temperature'))
h_col = cols_map.get('humidity')
m_col = cols_map.get('moisture')
crop_col = cols_map.get('crop type', cols_map.get('crop', cols_map.get('label')))

required = [n_col, p_col, k_col, t_col, h_col, m_col, crop_col]
if any(c is None for c in required):
    raise RuntimeError(f'Missing expected columns; found {list(df.columns)}')

# prepare dataframe
features = [n_col, p_col, k_col, t_col, h_col, m_col]
X = df[features].apply(pd.to_numeric, errors='coerce')
y = df[crop_col].astype(str).str.strip()

# Drop rows with any NA in features or label
mask = X.notnull().all(axis=1) & y.notnull()
X = X[mask]
y = y[mask]
print(f'Using {len(X)} rows after dropping NA')

full = X.copy()
full['crop'] = y.values

# Per-class stats
per_class = full.groupby('crop').agg(['mean', 'std', 'count'])
per_class.to_csv(os.path.join(OUT, 'per_class_stats.csv'))

# Mutual information (requires numeric X and encoded y)
from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()
y_enc = le.fit_transform(y)
mi = mutual_info_classif(X, y_enc, discrete_features=False, random_state=42)
mi_df = pd.DataFrame({'feature': X.columns, 'mutual_info': mi}).sort_values('mutual_info', ascending=False)
mi_df.to_csv(os.path.join(OUT, 'mutual_info.csv'), index=False)

# Boxplots per feature
for col in X.columns:
    plt.figure(figsize=(10,6))
    sns.boxplot(x=full['crop'], y=full[col])
    plt.xticks(rotation=45, ha='right')
    plt.title(f'Boxplot of {col} by crop')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, f'boxplot_{col}.png'), dpi=150)
    plt.close()

# Pairplot for top 3 features
top_feats = mi_df['feature'].tolist()[:3]
pp = sns.pairplot(full[top_feats + ['crop']], hue='crop', corner=True, plot_kws={'s':20, 'alpha':0.6})
pp_file = os.path.join(OUT, 'pairplot_top3.png')
pp.savefig(pp_file)
plt.close()

# Correlation heatmap
corr = X.corr()
plt.figure(figsize=(8,6))
sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm')
plt.title('Feature Correlation')
plt.tight_layout()
plt.savefig(os.path.join(OUT, 'feature_correlation.png'), dpi=150)
plt.close()

# Simple separability notes
notes = []
notes.append(f'Total samples used: {len(X)}')
notes.append('\nTop mutual information ranking:')
for i, row in mi_df.iterrows():
    notes.append(f"- {row['feature']}: {row['mutual_info']:.4f}")

# Count classes
class_counts = full['crop'].value_counts().sort_values(ascending=False)
notes.append('\nClass counts (top 10):')
for c, v in class_counts.items():
    notes.append(f'- {c}: {v}')

# Save notes
with open(os.path.join(OUT, 'eda_summary.md'), 'w', encoding='utf-8') as f:
    f.write('# EDA Summary\n\n')
    f.write('\n'.join(notes))

print('EDA complete. Outputs saved to', OUT)
