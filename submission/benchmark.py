"""LightGBM benchmark on the Kaggle Credit Card Fraud dataset (Lab 16)."""
import json
import os
import platform
import time

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split

DATA_PATH = os.path.expanduser("~/ml-benchmark/creditcard.csv")
OUT_PATH = "benchmark_result.json"

# 1. Load data
t0 = time.perf_counter()
df = pd.read_csv(DATA_PATH)
load_time = time.perf_counter() - t0
print(f"Loaded {len(df):,} rows x {df.shape[1]} cols in {load_time:.3f}s")

X = df.drop(columns=["Class"])
y = df["Class"]
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42)
X_tr, X_val, y_tr, y_val = train_test_split(
    X_train, y_train, test_size=0.1, stratify=y_train, random_state=42)

# 2. Train
model = lgb.LGBMClassifier(
    n_estimators=1000,
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=50,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    metric="auc",  # only track AUC so early stopping isn't driven by logloss
    n_jobs=-1,
    random_state=42,
    verbose=-1,
)
t0 = time.perf_counter()
model.fit(
    X_tr, y_tr,
    eval_set=[(X_val, y_val)],
    callbacks=[lgb.early_stopping(100, first_metric_only=True, verbose=False)],
)
train_time = time.perf_counter() - t0
best_iter = int(model.best_iteration_ or model.n_estimators)
print(f"Training time: {train_time:.3f}s (best iteration: {best_iter})")

# 3. Evaluate
proba = model.predict_proba(X_test)[:, 1]
pred = (proba >= 0.5).astype(int)
metrics = {
    "auc_roc": roc_auc_score(y_test, proba),
    "accuracy": accuracy_score(y_test, pred),
    "f1_score": f1_score(y_test, pred),
    "precision": precision_score(y_test, pred),
    "recall": recall_score(y_test, pred),
}
for k, v in metrics.items():
    print(f"{k:>10}: {v:.4f}")

# 4. Inference latency (1 row) & throughput (1000 rows)
one_row = X_test.iloc[[0]]
for _ in range(10):  # warm-up
    model.predict_proba(one_row)
lat = []
for _ in range(100):
    t0 = time.perf_counter()
    model.predict_proba(one_row)
    lat.append(time.perf_counter() - t0)
latency_ms = float(np.median(lat) * 1000)

batch = X_test.iloc[:1000]
runs = []
for _ in range(10):
    t0 = time.perf_counter()
    model.predict_proba(batch)
    runs.append(time.perf_counter() - t0)
batch_ms = float(np.median(runs) * 1000)
throughput = 1000 / (batch_ms / 1000)
print(f"Inference latency (1 row): {latency_ms:.3f} ms")
print(f"Inference 1000 rows: {batch_ms:.3f} ms ({throughput:,.0f} rows/s)")

# 5. Save
result = {
    "machine": platform.node(),
    "cpu_count": os.cpu_count(),
    "dataset_rows": len(df),
    "load_time_s": round(load_time, 4),
    "train_time_s": round(train_time, 4),
    "best_iteration": best_iter,
    **{k: round(float(v), 6) for k, v in metrics.items()},
    "inference_latency_1row_ms": round(latency_ms, 4),
    "inference_1000rows_ms": round(batch_ms, 4),
    "inference_throughput_rows_per_s": round(throughput, 1),
}
with open(OUT_PATH, "w") as f:
    json.dump(result, f, indent=2)
print(f"\nSaved results to {OUT_PATH}")
print(json.dumps(result, indent=2))
