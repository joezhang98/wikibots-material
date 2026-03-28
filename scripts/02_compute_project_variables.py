"""
Stage 11: Compute project page and project talk variables for each WikiProject.

Runs sequentially (one project at a time). Each project takes a few seconds.
Total: ~1-2 hours for all 763 WikiProjects; under a minute for demo (10 projects).

Inputs:
  raw/project/<project_id>_revision_history.csv
  raw/project_talk/<project_talk_id>_revision_history.csv

Outputs:
  variables/project_page/<index>_<project_id>_variables.csv
  variables/project_talk/<index>_<project_id>_variables.csv

Usage:
  python scripts/02_compute_project_variables.py          # demo
  python scripts/02_compute_project_variables.py --full
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collection_utils import (
    ALL_ARTICLE_INFO_FILE, VARIABLES_DIR,
    get_ordered_project_sample_df, get_bot_category_helper_structures,
    init_project_page_dict, init_project_talk_dict,
    compute_project_page_variables, compute_project_talk_variables,
)

DEMO_N = 1


def main():
    parser = argparse.ArgumentParser(
        description='Compute project page and project talk variables.'
    )
    parser.add_argument('--full', action='store_true',
                        help='Process all WikiProjects (default: demo subset of 10).')
    args = parser.parse_args()
    demo = not args.full

    project_page_dir = VARIABLES_DIR / 'project_page'
    project_talk_dir = VARIABLES_DIR / 'project_talk'
    project_page_dir.mkdir(parents=True, exist_ok=True)
    project_talk_dir.mkdir(parents=True, exist_ok=True)

    print('Loading metadata CSV (this may take 1-2 minutes)...')
    all_article_info_df = pd.read_csv(ALL_ARTICLE_INFO_FILE)
    project_to_articles_df = get_ordered_project_sample_df(all_article_info_df)

    if demo:
        project_to_articles_df = project_to_articles_df.iloc[:DEMO_N]
        print(f'Demo mode: processing {DEMO_N} smallest WikiProjects.')
    else:
        print(f'Full mode: processing {len(project_to_articles_df)} WikiProjects.')

    print('Loading bot category helper structures...')
    bots_map, bot_cat_voting_rule_lists = get_bot_category_helper_structures()

    for index, row in tqdm(project_to_articles_df.iterrows(),
                           total=len(project_to_articles_df)):
        project_id      = row['project_page_id']
        project_talk_id = row['project_talk_id']

        # --- Project page ---
        page_save = project_page_dir / f'{index}_{project_id}_variables.csv'
        if not page_save.exists():
            try:
                project_dict = init_project_page_dict(project_id)
                project_dict = compute_project_page_variables(
                    project_id, project_dict, bots_map, bot_cat_voting_rule_lists
                )
                pd.DataFrame(project_dict).to_csv(page_save, index=False, encoding='utf-8')
            except Exception as e:
                print(f'\nSkipping project page {project_id} (index {index}): {e}')

        # --- Project talk ---
        talk_save = project_talk_dir / f'{index}_{project_id}_variables.csv'
        if not talk_save.exists():
            try:
                talk_dict = init_project_talk_dict(project_id)
                talk_dict = compute_project_talk_variables(
                    project_talk_id, talk_dict, bots_map, bot_cat_voting_rule_lists
                )
                pd.DataFrame(talk_dict).to_csv(talk_save, index=False, encoding='utf-8')
            except Exception as e:
                print(f'\nSkipping project talk {project_talk_id} (index {index}): {e}')

    print('Done.')


if __name__ == '__main__':
    main()
