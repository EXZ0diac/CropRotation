#!/usr/bin/env python3
"""
merge_by_index.py

Copy matching columns from an auxiliary CSV into the main `datacore.csv` by positional/index alignment.

This overwrites target columns in the main file with values from the auxiliary file (useful when files are row-aligned but column names differ).

Writes `datacore_posmerged.csv` and `datacore_posmerged_report.json`.
"""
from __future__ import annotations

import json
import os
import sys
from typing import List

import pandas as pd


TARGET_COLUMNS = [
    "ph",
    "organic_carbon",
    "soil_type",
    "fertilizer_name",
    "region",
    "date",
    "ec",
]


def normalize_col(s: str) -> str:
    return str(s).strip().lower().replace(" ", "_").replace("-", "_")


def main():
    main_path = "datacore.csv"
    aux_path = "data_core_original.csv"
    out_csv = "datacore_posmerged.csv"
    out_report = "datacore_posmerged_report.json"

    if not os.path.exists(main_path):
        print(f"Main file {main_path} not found", file=sys.stderr)
        return
    if not os.path.exists(aux_path):
        print(f"Aux file {aux_path} not found", file=sys.stderr)
        return

    df_main = pd.read_csv(main_path)
    df_aux = pd.read_csv(aux_path)

    # normalize aux column names
    aux_cols_map = {c: normalize_col(c) for c in df_aux.columns}
    df_aux.rename(columns=aux_cols_map, inplace=True)

    # normalize main columns too
    main_cols_map = {c: normalize_col(c) for c in df_main.columns}
    df_main.rename(columns=main_cols_map, inplace=True)

    report = {
        "main_rows": int(df_main.shape[0]),
        "aux_rows": int(df_aux.shape[0]),
        "copied_columns": {},
    }

    # align lengths
    if df_main.shape[0] != df_aux.shape[0]:
        print("Warning: main and aux have different row counts; copying will use min length and preserve remaining rows")

    n = min(df_main.shape[0], df_aux.shape[0])

    for col in TARGET_COLUMNS:
        if col in df_aux.columns:
            # copy by position for the overlapping range, leave rest intact
            before_missing = int(df_main[col].isna().sum()) if col in df_main.columns else None
            df_main.loc[: n - 1, col] = df_aux.loc[: n - 1, col].values
            after_missing = int(df_main[col].isna().sum())
            report["copied_columns"][col] = {"from_aux": True, "before_missing": before_missing, "after_missing": after_missing}
        else:
            report["copied_columns"][col] = {"from_aux": False}

    # ensure columns order: keep existing main order, append any new columns from aux
    for col in df_aux.columns:
        if col not in df_main.columns:
            df_main[col] = df_aux[col]

    df_main.to_csv(out_csv, index=False)
    with open(out_report, "w", encoding="utf8") as fh:
        json.dump(report, fh, indent=2)

    print(f"Wrote {out_csv} and {out_report}")


if __name__ == "__main__":
    main()
