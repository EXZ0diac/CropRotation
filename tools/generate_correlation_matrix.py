"""
Generate a correlation matrix (CSV + heatmap PNG) for the synthetic training data used by model_training.py.
Reproduces the deterministic data generation so the matrix matches training inputs.

Outputs:
 - artifacts/correlation_matrix.csv
 - artifacts/correlation_heatmap.png

Usage:
 python tools/generate_correlation_matrix.py
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# deterministic seed (match model_training.py)
SEED = 42
np.random.seed(SEED)

crops = ["Paddy","Maize","Chili","Cucumber","Groundnut","Spinach"]

soil_midpoints = {
    "Paddy":      [95.0,47.5,47.5,6.65,62.5,30.0],
    "Maize":      [75.0,37.5,37.5,6.2,57.5,28.0],
    "Chili":      [55.0,57.5,42.5,6.0,52.5,31.0],
    "Cucumber":   [65.0,42.5,52.5,6.2,67.5,27.0],
    "Groundnut":  [45.0,27.5,32.5,6.45,52.5,29.0],
    "Spinach":    [35.0,17.5,22.5,6.75,67.5,23.0]
}

# Augmentation parameters (match model_training.py)
repeat = 600
noise_scale = [6.0, 6.0, 6.0, 0.25, 6.0, 1.5]

rows = []
labels = []
for crop in crops:
    midpoint = np.array(soil_midpoints[crop], dtype=float)
    for _ in range(repeat):
        noise = np.random.normal(scale=noise_scale)
        sample = midpoint + noise
        # clip to realistic ranges (same logic as model_training)
        sample[0:3] = np.clip(sample[0:3], 0, 300)
        sample[3] = np.clip(sample[3], 3.0, 9.0)
        sample[4] = np.clip(sample[4], 0, 100)
        sample[5] = np.clip(sample[5], -10, 50)
        rows.append(sample.tolist())
        labels.append(crop)

# column names used across the project
columns = ["N","P","K","pH","Moisture","Temperature"]

df = pd.DataFrame(rows, columns=columns)
# optionally add label column for grouping or future use
df['Crop'] = labels

# compute Pearson correlation matrix (numeric columns only)
corr = df[columns].corr(method='pearson')

# ensure output dir
os.makedirs('artifacts', exist_ok=True)

# save CSV
csv_path = os.path.join('artifacts', 'correlation_matrix.csv')
corr.to_csv(csv_path)
print(f"Saved correlation matrix CSV to: {csv_path}")

# print matrix to console
print('\nCorrelation matrix (Pearson):\n')
print(corr.round(3))

# draw heatmap
plt.figure(figsize=(8,6))
sns.set(context='notebook', style='white')
ax = sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', vmin=-1, vmax=1, square=True, linewidths=0.5)
ax.set_title('Feature Correlation Matrix')
plt.tight_layout()

png_path = os.path.join('artifacts', 'correlation_heatmap.png')
plt.savefig(png_path, dpi=200)
plt.close()
print(f"Saved correlation heatmap PNG to: {png_path}")

# Also print top absolute correlations (excluding self-correlation)
abs_corr = corr.abs()
# mask diagonal
for i in range(len(abs_corr)):
    abs_corr.iat[i, i] = 0.0

# flatten and sort
flat = abs_corr.unstack().sort_values(ascending=False)
# take top 6 unique pairs
seen = set()
pairs = []
for (a, b), val in flat.items():
    pair = tuple(sorted((a, b)))
    if pair in seen:
        continue
    seen.add(pair)
    pairs.append(((a, b), val))
    if len(pairs) >= 6:
        break

print('\nTop absolute correlations (excluding self):')
for (a, b), val in pairs:
    print(f"{a} <-> {b}: {val:.3f}")

print('\nDone.')
