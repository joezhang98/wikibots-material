"""
Stage 05: Assemble the final project-level panel dataset.

Loads the four per-project variable CSV directories, renames columns to their
final names, concatenates across all WikiProjects, adds year_month and
month_count columns, and saves the final CSV.

The column naming convention used here matches the column names in the
provided final dataset (data/full_sample_project_level_variables.csv),
so the output can be validated against the original.

Inputs:
  variables/project_page/<index>_<project_id>_variables.csv
  variables/project_talk/<index>_<project_id>_variables.csv
  variables/article_page/<index>_<project_id>_variables.csv
  variables/article_talk/<index>_<project_id>_variables.csv

Output:
  processed/full_sample_project_level_variables_<date>.csv

Usage:
  python scripts/05_assemble_dataset.py          # demo (assembles whatever is computed)
  python scripts/05_assemble_dataset.py --full
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collection_utils import (
    ALL_ARTICLE_INFO_FILE, VARIABLES_DIR, ROOT_DIR,
    get_ordered_project_sample_df,
    populate_renaming_dict_with_common_values,
    ASSESSMENT_CATEGORIES, NUM_MONTHS,
    get_year_month_from_index,
)

DEMO_N = 1


def build_renaming_dicts():
    """
    Build per-source column renaming dicts that map internal variable names
    to their final output column names (matching the provided final dataset).
    """
    # Project page variables: prefix wp_page
    proj_page = {
        'project_id':              'wp_id',
        'days_since_creation':     'wp_days_created',
        'article_alerts_present':  'wp_page_alerting',
        'avg_page_length':         'wp_page_len',
    }
    proj_page = populate_renaming_dict_with_common_values(proj_page, 'wp_page')

    # Project talk variables: prefix wp_talk
    proj_talk = {'avg_page_length': 'wp_talk_len'}
    proj_talk = populate_renaming_dict_with_common_values(proj_talk, 'wp_talk')

    # Article page variables: prefix art_page
    # project_size = number of articles in the WikiProject at each month
    art_page = {'project_size': 'wp_size'}
    art_page = populate_renaming_dict_with_common_values(art_page, 'art_page')

    # Article talk variables: prefix art_talk
    # Includes quality assessments (qual_fa, qual_ga, ..., qual_stub)
    art_talk = {}
    art_talk = populate_renaming_dict_with_common_values(art_talk, 'art_talk')
    for cat in ASSESSMENT_CATEGORIES:
        art_talk[f'num_rated_{cat}'] = f'qual_{cat}'

    return proj_page, proj_talk, art_page, art_talk


def main():
    parser = argparse.ArgumentParser(description='Assemble final panel dataset.')
    parser.add_argument('--full', action='store_true',
                        help='Assemble all projects (default: demo subset of 10).')
    parser.add_argument('--date', default=None,
                        help='Version date string to embed in output filename '
                             '(default: today, e.g. 03_22_2026).')
    args = parser.parse_args()
    demo = not args.full

    version_date = args.date or date.today().strftime('%m_%d_%Y')

    proj_page_dir = VARIABLES_DIR / 'project_page'
    proj_talk_dir = VARIABLES_DIR / 'project_talk'
    art_page_dir  = VARIABLES_DIR / 'article_page'
    art_talk_dir  = VARIABLES_DIR / 'article_talk'

    processed_dir = ROOT_DIR / 'processed'
    processed_dir.mkdir(parents=True, exist_ok=True)

    print('Loading metadata CSV (this may take 1-2 minutes)...')
    all_article_info_df = pd.read_csv(ALL_ARTICLE_INFO_FILE)
    project_to_articles_df = get_ordered_project_sample_df(all_article_info_df)

    if demo:
        project_to_articles_df = project_to_articles_df.iloc[:DEMO_N]
        print(f'Demo mode: assembling {DEMO_N} smallest WikiProjects.')
    else:
        print(f'Full mode: assembling {len(project_to_articles_df)} WikiProjects.')

    proj_page_rename, proj_talk_rename, art_page_rename, art_talk_rename = build_renaming_dicts()

    concat_df = None
    all_missing = []  # paths of missing variable files across all projects

    for index, row in tqdm(project_to_articles_df.iterrows(),
                           total=len(project_to_articles_df)):
        project_id = row['project_page_id']
        pp_path = proj_page_dir / f'{index}_{project_id}_variables.csv'
        pt_path = proj_talk_dir / f'{index}_{project_id}_variables.csv'
        ap_path = art_page_dir  / f'{index}_{project_id}_variables.csv'
        at_path = art_talk_dir  / f'{index}_{project_id}_variables.csv'

        # Check all four variable files exist before trying to read them
        project_missing = [str(p) for p in [pp_path, pt_path, ap_path, at_path]
                           if not p.exists()]
        if project_missing:
            all_missing.extend(project_missing)
            continue

        # Rename to final column names and select only the expected columns
        proj_page_df = pd.read_csv(pp_path).rename(columns=proj_page_rename)[list(proj_page_rename.values())]
        proj_talk_df = pd.read_csv(pt_path).rename(columns=proj_talk_rename)[list(proj_talk_rename.values())]
        art_page_df  = pd.read_csv(ap_path).rename(columns=art_page_rename)[list(art_page_rename.values())]
        art_talk_df  = pd.read_csv(at_path).rename(columns=art_talk_rename)[list(art_talk_rename.values())]

        # Concatenate horizontally (same 288-row index for all four sources).
        # Build time columns as a DataFrame first to avoid fragmentation warnings.
        time_df = pd.DataFrame({
            'year_month':  [get_year_month_from_index(i) for i in range(NUM_MONTHS)],
            'month_count': list(range(NUM_MONTHS)),
        })
        merged = pd.concat([proj_page_df, proj_talk_df, art_page_df, art_talk_df, time_df], axis=1)

        concat_df = merged if concat_df is None else pd.concat([concat_df, merged], axis=0)

    if all_missing:
        print(f'\nWARNING: {len(all_missing)} variable file(s) not found. '
              f'Run stages 02-04 first.')
        for p in all_missing[:10]:
            print(f'  Missing: {p}')
        if len(all_missing) > 10:
            print(f'  ... and {len(all_missing) - 10} more.')
        if concat_df is None:
            print('No data assembled. Exiting.')
            sys.exit(1)

    save_path = processed_dir / f'full_sample_project_level_variables_{version_date}.csv'
    concat_df.to_csv(save_path, index=False, encoding='utf-8')
    print(f'\nSaved: {save_path}')
    print(f'Shape: {concat_df.shape[0]} rows × {concat_df.shape[1]} columns '
          f'({concat_df.shape[0] // NUM_MONTHS} WikiProjects × {NUM_MONTHS} months)')


if __name__ == '__main__':
    main()
