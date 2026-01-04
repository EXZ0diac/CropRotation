#!/usr/bin/env python3
"""Trim the filtered CSV to only the user-specified columns.

Writes `datacore_filtered_trimmed.csv` and `datacore_filtered_trimmed_report.json`.
"""
from pathlib import Path
import sys
import json

import pandas as pd

KEEP = [
    'nitrogen',
    'potassium',
    'phosphorus',
    'temperature',
    'humidity',
    'moisture',
    'crop',
    'ph'
]


def find_column(df, candidates):
    # return column name from df that matches any candidate (case-insensitive or substring)
    found = {}
    for cand in candidates:
        for col in df.columns:
            if cand.lower() == col.lower() or cand.lower() in col.lower() or col.lower() in cand.lower():
                found[cand] = col
                break
    return found


def main():
    src = None
    for p in (Path('datacore_filtered.csv'), Path('datacore_prepared.csv'), Path('datacore.csv')):
        if p.exists():
            src = p
            break
    if src is None:
        print('No source datacore CSV found. Place `datacore_filtered.csv` or `datacore_prepared.csv` in the workspace.')
        sys.exit(1)

    df = pd.read_csv(src)
    mapping = find_column(df, KEEP)

    missing = [k for k in KEEP if k not in mapping]
    if missing:
        print('Warning: some requested columns not found in source:', missing)

    # build list of actual columns to keep (preserve crop column name)
    keep_cols = [mapping[k] for k in KEEP if k in mapping]
    # ensure 'crop' present
    if not any('crop' in c.lower() for c in keep_cols):
        # try to find crop column generically
        for col in df.columns:
            if 'crop' in col.lower():
                keep_cols.append(col)
                break

    trimmed = df[keep_cols].copy()

    out_csv = Path('datacore_filtered_trimmed.csv')
    out_report = Path('datacore_filtered_trimmed_report.json')
    trimmed.to_csv(out_csv, index=False)

    report = {
        'source': str(src),
        'rows': int(len(trimmed)),
        'kept_columns': keep_cols,
        'requested_keep': KEEP,
        'missing_requested': missing
    }
    out_report.write_text(json.dumps(report, indent=2))
    print('Wrote', out_csv, 'and', out_report)


if __name__ == '__main__':
    main()
