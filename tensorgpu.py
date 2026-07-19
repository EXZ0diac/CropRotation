# save as quick_checks.py and run: python quick_checks.py
import numpy as np
import tensorflow as tf
from math import ceil
import joblib
import pandas as pd

df = pd.read_csv("chili_eggplant_balanced_50150.csv")
X = df[["Nitrogen","Phosphorus","Potassium","pH","Humidity","Temperature"]].astype(float)
batch_size = 64   # match your script
n_train = int(len(X) * 0.70 * 0.7)  # approximate if you use 70/15/15 split; or compute from saved splits
print("Total samples:", len(df))
print("Example batch_size:", batch_size)
print("Train samples (approx):", n_train)
print("Steps per epoch (approx):", ceil(n_train / batch_size))
print("TensorFlow devices:", tf.config.list_physical_devices())