"""
Stage 13: Compute aggregated article talk variables for each WikiProject.

For each WikiProject, iterates over all its member article talk pages and
accumulates monthly edit statistics (including article quality
assessments), then saves one CSV per project.

In demo mode (default), processes 10 projects sequentially on 1 core.
In full mode, uses all available CPU cores via multiprocessing.Pool.

Inputs:
  raw/article_talk/<bucket>/<article_talk_id>_revision_history.csv

Outputs:
  variables/article_talk/<index>_<project_id>_variables.csv

Usage:
  python scripts/04_compute_article_talk_variables.py          # demo
  python scripts/04_compute_article_talk_variables.py --full
"""

import argparse
import multiprocessing as mp
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collection_utils import (
    ALL_ARTICLE_INFO_FILE, VARIABLES_DIR,
    get_ordered_project_sample_df, get_bot_category_helper_structures,
    init_aggregated_article_talk_project_dict,
    compute_article_talk_variables,
)

DEMO_N = 1

# ---------------------------------------------------------------------------
# Worker function (multiprocessing-compatible)
# ---------------------------------------------------------------------------

_bots_map = None
_bot_cat_voting_rule_lists = None
_save_dir = None


def _worker_init(bots_map_arg, bot_cat_voting_rule_lists_arg, save_dir_arg):
    global _bots_map, _bot_cat_voting_rule_lists, _save_dir
    _bots_map = bots_map_arg
    _bot_cat_voting_rule_lists = bot_cat_voting_rule_lists_arg
    _save_dir = Path(save_dir_arg)


def _compute_and_save(args):
    index, project_id, member_article_talk_ids = args
    save_path = _save_dir / f'{index}_{project_id}_variables.csv'
    if save_path.exists():
        return

    project_dict = init_aggregated_article_talk_project_dict(project_id)
    for article_talk_id in member_article_talk_ids:
        project_dict = compute_article_talk_variables(
            article_talk_id, project_dict, _bots_map, _bot_cat_voting_rule_lists
        )
    pd.DataFrame(project_dict).to_csv(save_path, index=False, encoding='utf-8')

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description='Compute aggregated article talk variables per WikiProject.'
    )
    parser.add_argument('--full', action='store_true',
                        help='Process all WikiProjects (default: demo subset of 10).')
    args = parser.parse_args()
    demo = not args.full

    save_dir = VARIABLES_DIR / 'article_talk'
    save_dir.mkdir(parents=True, exist_ok=True)

    print('Loading metadata CSV (this may take 1-2 minutes)...')
    all_article_info_df = pd.read_csv(ALL_ARTICLE_INFO_FILE)
    project_to_articles_df = get_ordered_project_sample_df(all_article_info_df)

    if demo:
        project_to_articles_df = project_to_articles_df.iloc[:DEMO_N]
        num_processes = 1
        print(f'Demo mode: processing {DEMO_N} smallest WikiProjects on 1 core.')
    else:
        num_processes = max(1, mp.cpu_count() - 2)
        print(f'Full mode: {len(project_to_articles_df)} WikiProjects '
              f'on {num_processes} cores.')

    print('Loading bot category helper structures...')
    bots_map, bot_cat_voting_rule_lists = get_bot_category_helper_structures()

    work_items = [
        (index, row['project_page_id'], row['member_article_talk_ids'])
        for index, row in project_to_articles_df.iterrows()
    ]

    if num_processes == 1:
        _worker_init(bots_map, bot_cat_voting_rule_lists, str(save_dir))
        for item in tqdm(work_items):
            _compute_and_save(item)
    else:
        initargs = (bots_map, bot_cat_voting_rule_lists, str(save_dir))
        with mp.Pool(processes=num_processes,
                     initializer=_worker_init,
                     initargs=initargs) as pool:
            for _ in tqdm(
                pool.imap_unordered(_compute_and_save, work_items),
                total=len(work_items),
            ):
                pass

    print('Done.')


if __name__ == '__main__':
    main()
