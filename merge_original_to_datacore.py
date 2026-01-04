import pandas as pd
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
orig_path = ROOT / 'data_core_original.csv'
core_path = ROOT / 'datacore.csv'
out_csv = ROOT / 'datacore_enriched.csv'
out_report = ROOT / 'datacore_enriched_report.json'

def normalize_cols(df):
    df.columns = [c.strip() for c in df.columns]
    return df

def main():
    if not orig_path.exists():
        print(f'missing {orig_path}')
        return
    if not core_path.exists():
        print(f'missing {core_path}')
        return

    orig = pd.read_csv(orig_path)
    core = pd.read_csv(core_path)
    orig = normalize_cols(orig)
    core = normalize_cols(core)

    # Map candidate columns from original to add into core
    # prefer names 'Soil Type' and 'Fertilizer Name' (case-sensitive in file)
    add_cols = {}
    for col in ['Soil Type', 'SoilType', 'Soil_Type', 'soil type']:
        if col in orig.columns:
            add_cols['soil_type'] = col
            break
    for col in ['Fertilizer Name', 'FertilizerName', 'Fertilizer_Name', 'fertilizer name']:
        if col in orig.columns:
            add_cols['fertilizer_name'] = col
            break

    # If original contains Crop Type but core has 'Crop Type' vs 'Crop Type', we'll keep core's label
    # Align by index: only up to min length
    n_orig = len(orig)
    n_core = len(core)
    n = min(n_orig, n_core)

    report = {
        'n_original_rows': int(n_orig),
        'n_core_rows': int(n_core),
        'n_merged_rows': int(n),
        'added_columns_found': list(add_cols.keys()),
        'notes': []
    }

    # Prepare enriched dataframe as copy of core
    enriched = core.copy()

    # Add columns if found, else create empty columns
    if 'soil_type' in add_cols:
        enriched['soil_type'] = orig[add_cols['soil_type']].astype(object).iloc[:n].values
    else:
        enriched['soil_type'] = pd.NA
        report['notes'].append('soil_type not found in original file; filled with NA')

    if 'fertilizer_name' in add_cols:
        enriched['fertilizer_name'] = orig[add_cols['fertilizer_name']].astype(object).iloc[:n].values
    else:
        enriched['fertilizer_name'] = pd.NA
        report['notes'].append('fertilizer_name not found in original file; filled with NA')

    # If orig contains N/P/K columns but in different order, do not overwrite core's numeric columns
    # Save enriched CSV (keep original column order + new columns)
    enriched.to_csv(out_csv, index=False)

    # Add simple diagnostics
    report['enriched_csv'] = str(out_csv.name)
    report['missing_values'] = {
        'soil_type_na_count': int(enriched['soil_type'].isna().sum()),
        'fertilizer_name_na_count': int(enriched['fertilizer_name'].isna().sum()),
    }

    with open(out_report, 'w', encoding='utf8') as f:
        json.dump(report, f, indent=2)

    print(f'Wrote {out_csv} and {out_report}')

if __name__ == '__main__':
    main()
