#!/usr/bin/env python3
"""
prepare_datacore.py

Small utility to validate, normalize, and augment `datacore.csv` for modeling.

Features:
- Normalizes column names and common synonyms
- Coerces numeric columns, preserving zeros and parsing decimals
- Adds recommended missing columns (ph, organic_carbon, soil_type, fertilizer_name, region, date, ec)
- Creates zero-indicator columns for N/P/K
- Optionally merges an auxiliary CSV (same-length or by `crop` key) to recover extra fields
- Writes cleaned CSV and a JSON cleaning report

Usage examples:
  python prepare_datacore.py --input datacore.csv --output datacore_cleaned.csv
  python prepare_datacore.py --input datacore.csv --merge original_kaggle.csv --output merged_cleaned.csv

"""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


def normalize_colname(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"[\s\-\/]+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"__+", "_", s)
    return s


STANDARD_COLS = {
    "nitrogen": ["nitrogen", "n"],
    "phosphorus": ["phosphorous", "phosphorus", "p"],
    "potassium": ["potassium", "k"],
    "temperature": ["temperature", "temparature", "temp"],
    "humidity": ["humidity", "humid"],
    "moisture": ["moisture", "soil_moisture", "moisture_percent"],
    "crop": ["crop", "crop_type", "label", "cropname"],
}

RECOMMENDED_ADDITIONAL = [
    "ph",
    "organic_carbon",
    "soil_type",
    "fertilizer_name",
    "region",
    "date",
    "ec",
]


def map_columns(cols: List[str]) -> Dict[str, str]:
    """Return mapping from existing column -> standardized name."""
    mapped = {}
    lower_cols = {normalize_colname(c): c for c in cols}
    for std, synonyms in STANDARD_COLS.items():
        found = None
        for cand in [std] + synonyms:
            nc = normalize_colname(cand)
            if nc in lower_cols:
                found = lower_cols[nc]
                break
        if found:
            mapped[found] = std

    # If crop column still not found, scan for any column containing 'crop' or 'type'
    if not any(v == "crop" for v in mapped.values()):
        for nc, orig in lower_cols.items():
            if "crop" in nc or ("type" in nc and "soil" not in nc):
                mapped[orig] = "crop"
                break

    return mapped


def coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def add_missing_columns(df: pd.DataFrame) -> pd.DataFrame:
    for c in RECOMMENDED_ADDITIONAL:
        if c not in df.columns:
            df[c] = np.nan
    return df


def add_zero_indicators(df: pd.DataFrame) -> pd.DataFrame:
    for nutrient in ["nitrogen", "phosphorus", "potassium"]:
        col = nutrient
        if col in df.columns:
            df[f"{col}_is_zero"] = (df[col] == 0).astype(int)
            df[f"{col}_was_missing"] = df[col].isna().astype(int)
    return df


def build_report(df: pd.DataFrame, original_rows: int, input_path: str) -> Dict:
    report = {
        "input_path": input_path,
        "rows_before": original_rows,
        "rows_after": int(df.shape[0]),
        "columns": list(df.columns),
        "missing_counts": df.isna().sum().to_dict(),
        "zero_counts": {c: int((df[c] == 0).sum()) for c in ["nitrogen", "phosphorus", "potassium"] if c in df.columns},
        "unique_crops": int(df["crop"].nunique()) if "crop" in df.columns else None,
        "sample_rows": df.head(3).to_dict(orient="records"),
    }
    return report


def try_merge_aux(df: pd.DataFrame, aux_path: str) -> pd.DataFrame:
    aux = pd.read_csv(aux_path)
    # Normalize aux columns
    aux_cols_norm = {c: normalize_colname(c) for c in aux.columns}
    aux.columns = [aux_cols_norm[c] for c in aux_cols_norm]

    # If same length, align by index and copy missing recommended columns into main df
    if aux.shape[0] == df.shape[0]:
        for c in RECOMMENDED_ADDITIONAL + ["soil_type", "fertilizer_name"]:
            if c in aux.columns and c not in df.columns:
                df[c] = aux[c]
        return df

    # Else try join on 'crop'
    if "crop" in aux.columns and "crop" in df.columns:
        merged = df.merge(aux, how="left", on="crop", suffixes=("", "_aux"))
        # If duplicates for recommended columns exist, prefer left-hand values then fill from aux
        for c in RECOMMENDED_ADDITIONAL + ["soil_type", "fertilizer_name"]:
            aux_c = c if c in merged.columns else f"{c}_aux"
            if aux_c in merged.columns:
                if c not in merged.columns:
                    merged[c] = merged[aux_c]
                else:
                    merged[c] = merged[c].fillna(merged[aux_c])
                if aux_c != c:
                    merged.drop(columns=[aux_c], inplace=True, errors=True)
        return merged

    # Fallback: nothing merged
    return df


def main():
    p = argparse.ArgumentParser(description="Prepare and augment datacore CSV for modeling")
    p.add_argument("--input", "-i", help="Input CSV path (default: datacore.csv or data_core.csv)", default=None)
    p.add_argument("--merge", "-m", help="Auxiliary CSV to merge (original Kaggle file with extra cols)", default=None)
    p.add_argument("--output", "-o", help="Output cleaned CSV path", default="datacore_cleaned.csv")
    p.add_argument("--report", "-r", help="JSON cleaning report path", default="datacore_cleaning_report.json")
    args = p.parse_args()

    candidates = []
    if args.input:
        candidates.append(args.input)
    candidates.extend(["datacore.csv", "data_core.csv", "data-core.csv", "data-core.csv"])

    input_path = None
    for c in candidates:
        if c and os.path.exists(c):
            input_path = c
            break

    if input_path is None:
        print("No input CSV found. Provide --input path or put `datacore.csv` in the current directory.")
        return

    print(f"Loading {input_path}...")
    df = pd.read_csv(input_path)
    original_rows = df.shape[0]

    # normalize columns
    orig_cols = list(df.columns)
    col_map_candidates = map_columns(orig_cols)
    df.rename(columns=col_map_candidates, inplace=True)

    # sanitize column names to normalized versions too
    df.columns = [normalize_colname(c) for c in df.columns]

    # coerce numeric
    numeric_cols = ["nitrogen", "phosphorus", "potassium", "temperature", "humidity", "moisture", "ec", "ph", "organic_carbon"]
    df = coerce_numeric(df, numeric_cols)

    # add recommended columns if missing
    df = add_missing_columns(df)

    # zero indicators
    df = add_zero_indicators(df)

    # optional merge
    if args.merge:
        if os.path.exists(args.merge):
            print(f"Merging auxiliary file {args.merge}...")
            df = try_merge_aux(df, args.merge)
        else:
            print(f"Auxiliary file {args.merge} not found; skipping merge.")

    # Ensure crop column exists
    if "crop" not in df.columns:
        # fallback: try to find any column that looks like a crop label
        for c in df.columns:
            if "crop" in c or ("label" in c and "soil" not in c):
                df.rename(columns={c: "crop"}, inplace=True)
                break

    report = build_report(df, original_rows, input_path)

    # Save outputs
    out_dir = os.path.dirname(os.path.abspath(args.output))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    df.to_csv(args.output, index=False)
    with open(args.report, "w", encoding="utf8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print(f"Wrote cleaned CSV -> {args.output}")
    print(f"Wrote report -> {args.report}")


if __name__ == "__main__":
    main()
