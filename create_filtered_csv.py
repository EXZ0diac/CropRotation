#!/usr/bin/env python3
"""Create a filtered CSV by removing specified crop classes.

Produces `datacore_filtered.csv` and `datacore_filtered_report.json`.
"""
from pathlib import Path
import sys
import json

import pandas as pd

REMOVALS = ['oil seeds', 'pulses', 'tobacco', 'cotton']


def find_column(df, candidates):
    for cand in candidates:
        for name in df.columns:
            if cand.lower() == name.lower() or cand.lower() in name.lower():
                return name
    return None


def main():
    for p in (Path('datacore_prepared.csv'), Path('datacore.csv')):
        if p.exists():
            df = pd.read_csv(p)
            print('Loaded', p)
            break
    else:
        print('No datacore CSV found.')
        sys.exit(1)

    target_col = find_column(df, ['crop', 'crop_type', 'crop type'])
    if target_col is None:
        print('Could not find crop column. Columns:', df.columns.tolist())
        sys.exit(2)

    before = len(df)
    mask_keep = ~df[target_col].astype(str).str.strip().str.lower().isin([r.lower() for r in REMOVALS])
    df_filtered = df[mask_keep].copy()
    after = len(df_filtered)

    out_csv = Path('datacore_filtered.csv')
    out_report = Path('datacore_filtered_report.json')
    df_filtered.to_csv(out_csv, index=False)

    report = {
        'source': str(p),
        'rows_before': int(before),
        'rows_after': int(after),
        'removed_rows': int(before - after),
        'removals': REMOVALS,
        'target_column': target_col
    }
    out_report.write_text(json.dumps(report, indent=2))
    print('Wrote', out_csv, 'and', out_report)


if __name__ == '__main__':
    main()
