"""
Shared utilities for the data collection and variable computation pipeline.
"""

from ast import literal_eval
from collections import Counter
import os
import pandas as pd
import re
import time
from pathlib import Path
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Directory layout
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR       = ROOT_DIR / 'data'
RAW_DIR        = ROOT_DIR / 'raw'
VARIABLES_DIR  = ROOT_DIR / 'variables'

PROJECT_PAGE_REV_DIR  = RAW_DIR / 'project'
PROJECT_TALK_REV_DIR  = RAW_DIR / 'project_talk'
ARTICLE_PAGE_REV_DIR  = RAW_DIR / 'article'
ARTICLE_TALK_REV_DIR  = RAW_DIR / 'article_talk'

ALL_ARTICLE_INFO_FILE = DATA_DIR / 'all_article_talk_and_project_info_filtered.csv'
ALL_BOTS_FILE         = DATA_DIR / 'Full_4932_LLMLabel_gpt-4o-2024-11-20.csv'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_MONTHS = 12 * 24  # 288 months: 2000-01 through 2023-12

ORIGINAL_BOT_LABELS = [
    'Operational', 'Interwiki', 'Information provision', 'Task allocation',
    'Task division', 'Exception management', 'Reward provision', 'Other'
]
BOT_CATEGORIES = ['op', 'iw', 'ip', 'ta', 'td', 'ex', 'rp', 'ot', 'mi']
BOT_CATEGORY_NAME_MAP = dict(zip(ORIGINAL_BOT_LABELS, BOT_CATEGORIES))
VOTING_RULES = ['uni', 'maj', 'freq', 'prop']  # 'prop' does not apply to 'mi'
BOT_REVS_PREFIX       = 'num_revs_bot_{}_{}'
ASSESSMENT_CATEGORIES = ['fa', 'ga', 'a', 'b', 'c', 'start', 'stub']

PROJECT_PAGE_REV_COLS  = ['revid', 'timestamp', 'user', 'size', 'content']
PROJECT_TALK_REV_COLS  = ['revid', 'timestamp', 'user', 'size']
ARTICLE_PAGE_REV_COLS  = ['revid', 'timestamp', 'user', 'size']
ARTICLE_TALK_REV_COLS  = ['revid', 'timestamp', 'user', 'assessment']

YEAR_MONTH_NAME = 'year_month'
YEAR_MONTH_CODE = '%Y-%m'

# Column renaming maps used by 05_assemble_dataset.py
COMMON_KEYS_AND_VALUE_SUFFIXES = {
    'num_revs':         'revs',
    'num_revs_human':   'human_revs',
    'num_revs_bot_all': 'bot_revs',
}

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def get_ordered_project_sample_df(source_df):
    """Build a per-project DataFrame sorted ascending by article count."""
    article_membership = pd.DataFrame(
        source_df.groupby(['project_page_id', 'project_talk_id', 'project_page_title'])
                 ['corresponding_page_id'].apply(set)
    ).reset_index()
    article_talk_membership = pd.DataFrame(
        source_df.groupby(['project_page_id', 'project_talk_id', 'project_page_title'])
                 ['page_id'].apply(set)
    ).reset_index()
    merged = article_membership.merge(
        article_talk_membership, how='right',
        on=['project_page_id', 'project_talk_id', 'project_page_title']
    )
    merged.rename(columns={
        'corresponding_page_id': 'member_article_ids',
        'page_id': 'member_article_talk_ids'
    }, inplace=True)
    merged['num_member_article_ids']      = merged['member_article_ids'].apply(len)
    merged['num_member_article_talk_ids'] = merged['member_article_talk_ids'].apply(len)
    merged = merged.sort_values(
        by=['num_member_article_ids', 'project_page_id'], kind='mergesort', ascending=True
    ).reset_index(drop=True)
    return merged


def get_article_path(id, rev_dir):
    """Return the Path to a per-article revision history CSV."""
    lower = (id // 10000) * 10000
    upper = lower + 9999
    return rev_dir / f'{lower}_{upper}' / f'{id}_revision_history.csv'


def standardize_columns(df):
    if 'content' in df.columns:
        df['content'] = df['content'].astype(str)
    if 'user' in df.columns:
        df['user'] = df['user'].astype(str)
    if 'userid' in df.columns:
        df['userid'] = df['userid'].fillna(-1).astype(int)
    return df


def get_index_from_year_month(year_month):
    year  = int(year_month.split('-')[0])
    month = int(year_month.split('-')[1])
    return (year - 2000) * 12 + (month - 1)


def get_year_month_from_index(index):
    year  = (index // 12) + 2000
    month = (index % 12) + 1
    return '{}-{:02d}'.format(year, month)


def compute_presence_of_article_alerts(row):
    return 1 if 'Article alerts' in row['content'] else 0


def compute_page_assessment(assessment_list_literal):
    if not isinstance(assessment_list_literal, str):
        return None
    assessment_list = literal_eval(assessment_list_literal)
    for assessment_cat in ASSESSMENT_CATEGORIES:
        for assessment in assessment_list:
            if 'class={}'.format(assessment_cat) in assessment.replace(' ', ''):
                return assessment_cat
    return None


def populate_renaming_dict_with_common_values(renaming_dict, page_type_prefix):
    for k, v in COMMON_KEYS_AND_VALUE_SUFFIXES.items():
        renaming_dict[k] = '{}_{}'.format(page_type_prefix, v)
    for bot_cat in BOT_CATEGORIES:
        for vote in VOTING_RULES:
            if bot_cat == 'mi' and vote == 'prop':
                continue
            renaming_dict[BOT_REVS_PREFIX.format(bot_cat, vote)] = \
                '{}_bot_{}_{}_revs'.format(page_type_prefix, bot_cat, vote)
    return renaming_dict

# ---------------------------------------------------------------------------
# Helper structures
# ---------------------------------------------------------------------------

def get_bot_category_helper_structures():
    """Return (bots_map, bot_cat_voting_rule_lists) from the bot-labels CSV."""
    all_bot_info_df = pd.read_csv(ALL_BOTS_FILE)
    all_bot_info_df['Category'] = all_bot_info_df['gpt-4o-2024-11-20'].map(BOT_CATEGORY_NAME_MAP)

    bots_map = {}
    for bot in all_bot_info_df['Bot'].unique():
        bot_df  = all_bot_info_df[all_bot_info_df['Bot'] == bot]
        labels  = [row['Category'] for _, row in bot_df.iterrows()]
        counter = Counter(labels)
        total   = len(labels)

        proportions = {key: counter[key] / total for key in BOT_CATEGORIES}
        unanimous   = next(iter(counter)) if len(counter) == 1 else 'mi'
        majority_fracs = [v / total for v in counter.values()]
        majority = (
            max(counter, key=counter.get)
            if sum(1 for f in majority_fracs if f >= 0.5) == 1
            else 'mi'
        )
        max_count = max(counter.values())
        most_frequent = (
            max(counter, key=counter.get)
            if list(counter.values()).count(max_count) == 1
            else 'mi'
        )

        bot_tasks = {row['Bot Task']: row['Category'] for _, row in bot_df.iterrows()}
        bots_map[bot] = {
            'bot_tasks': bot_tasks,
            'uni':  unanimous,
            'maj':  majority,
            'freq': most_frequent,
            'prop': proportions,
        }

    bot_cat_voting_rule_lists = {
        '{}_{}'.format(bc, v): []
        for bc in BOT_CATEGORIES
        for v in VOTING_RULES
        if v != 'prop'
    }
    for bot_name, details in bots_map.items():
        for vote in ['uni', 'maj', 'freq']:
            bot_cat_voting_rule_lists['{}_{}'.format(details[vote], vote)].append(bot_name)

    return bots_map, bot_cat_voting_rule_lists

# ---------------------------------------------------------------------------
# Dict initializers
# ---------------------------------------------------------------------------

def init_project_dict_base(id):
    d = {'project_id': id}
    d['num_revs']       = [0] * NUM_MONTHS
    d['num_revs_human'] = [0] * NUM_MONTHS
    d['num_revs_bot_all'] = [0] * NUM_MONTHS

    for bot_cat in BOT_CATEGORIES:
        for vote in VOTING_RULES:
            if bot_cat == 'mi' and vote == 'prop':
                continue
            d[BOT_REVS_PREFIX.format(bot_cat, vote)] = [0] * NUM_MONTHS
    return d


def init_aggregated_article_project_dict(id):
    d = init_project_dict_base(id)
    d['project_size'] = [0] * NUM_MONTHS
    return d


def init_aggregated_article_talk_project_dict(id):
    d = init_project_dict_base(id)
    for cat in ASSESSMENT_CATEGORIES:
        d['num_rated_{}'.format(cat)] = [0] * NUM_MONTHS
    return d


def init_project_page_dict(id):
    d = init_project_dict_base(id)
    d['avg_page_length']       = [0] * NUM_MONTHS
    d['days_since_creation']   = [0] * NUM_MONTHS
    d['article_alerts_present']= [0] * NUM_MONTHS
    return d


def init_project_talk_dict(id):
    d = init_project_dict_base(id)
    d['avg_page_length'] = [0] * NUM_MONTHS
    return d

# ---------------------------------------------------------------------------
# Variable computation: project page
# ---------------------------------------------------------------------------

def compute_project_page_variables(id, project_dict, bots_map, bot_cat_voting_rule_lists):
    csv_path = PROJECT_PAGE_REV_DIR / f'{id}_revision_history.csv'
    project_rev = pd.read_csv(csv_path, usecols=PROJECT_PAGE_REV_COLS)
    project_rev = standardize_columns(project_rev)
    project_rev[YEAR_MONTH_NAME] = (
        pd.to_datetime(project_rev['timestamp'], format='mixed')
        .dt.strftime(YEAR_MONTH_CODE)
    )
    project_rev = project_rev[project_rev[YEAR_MONTH_NAME] < '2024-01']
    project_rev['article_alerts_present'] = project_rev.apply(
        compute_presence_of_article_alerts, axis=1
    )
    project_rev['timestamp'] = pd.to_datetime(
        project_rev['timestamp'], format='mixed', utc=True
    ).dt.tz_localize(None)
    first_revision_date = project_rev['timestamp'].iloc[0]

    for i in range(NUM_MONTHS):
        year_month_end = pd.to_datetime(get_year_month_from_index(i)) + pd.offsets.MonthEnd(0)
        project_dict['days_since_creation'][i] = max(
            0, (year_month_end - first_revision_date).days
        )

    project_rev_groupby = project_rev.groupby(YEAR_MONTH_NAME, as_index=False, sort=False)
    for _, (year_month, group) in enumerate(project_rev_groupby):
        idx = get_index_from_year_month(year_month)
        article_alerts_present = group.iloc[-1]['article_alerts_present']
        avg_page_length = group['size'].mean()
        for i in range(idx, NUM_MONTHS):
            project_dict['article_alerts_present'][i] = article_alerts_present
            project_dict['avg_page_length'][i] = avg_page_length

        project_dict['num_revs'][idx] += len(group)

        group_human = group[~group['user'].isin(bots_map)]
        project_dict['num_revs_human'][idx] += len(group_human)

        group_bot_all = group[group['user'].isin(bots_map)]
        project_dict['num_revs_bot_all'][idx] += len(group_bot_all)

        for bot_cat in BOT_CATEGORIES:
            for vote in VOTING_RULES:
                if vote == 'prop':
                    continue
                subset = group[group['user'].isin(bot_cat_voting_rule_lists['{}_{}'.format(bot_cat, vote)])]
                project_dict[BOT_REVS_PREFIX.format(bot_cat, vote)][idx] += len(subset)

        for _, bot_rev in group_bot_all.iterrows():
            bot_name = bot_rev['user']
            for bot_cat in BOT_CATEGORIES:
                if bots_map[bot_name]['prop'][bot_cat] > 0:
                    project_dict[BOT_REVS_PREFIX.format(bot_cat, 'prop')][idx] += \
                        bots_map[bot_name]['prop'][bot_cat]

    return project_dict

# ---------------------------------------------------------------------------
# Variable computation: project talk
# ---------------------------------------------------------------------------

def compute_project_talk_variables(id, project_dict, bots_map, bot_cat_voting_rule_lists):
    csv_path = PROJECT_TALK_REV_DIR / f'{id}_revision_history.csv'
    project_rev = pd.read_csv(csv_path, usecols=PROJECT_TALK_REV_COLS)
    project_rev = standardize_columns(project_rev)
    project_rev[YEAR_MONTH_NAME] = (
        pd.to_datetime(project_rev['timestamp'], format='mixed')
        .dt.strftime(YEAR_MONTH_CODE)
    )
    project_rev = project_rev[project_rev[YEAR_MONTH_NAME] < '2024-01']

    for _, (year_month, group) in enumerate(
        project_rev.groupby(YEAR_MONTH_NAME, as_index=False, sort=False)
    ):
        idx = get_index_from_year_month(year_month)
        avg_page_length = group['size'].mean()
        for i in range(idx, NUM_MONTHS):
            project_dict['avg_page_length'][i] = avg_page_length

        project_dict['num_revs'][idx] += len(group)

        group_human = group[~group['user'].isin(bots_map)]
        project_dict['num_revs_human'][idx] += len(group_human)

        group_bot_all = group[group['user'].isin(bots_map)]
        project_dict['num_revs_bot_all'][idx] += len(group_bot_all)

        for bot_cat in BOT_CATEGORIES:
            for vote in VOTING_RULES:
                if vote == 'prop':
                    continue
                subset = group[group['user'].isin(bot_cat_voting_rule_lists['{}_{}'.format(bot_cat, vote)])]
                project_dict[BOT_REVS_PREFIX.format(bot_cat, vote)][idx] += len(subset)

        for _, bot_rev in group_bot_all.iterrows():
            bot_name = bot_rev['user']
            for bot_cat in BOT_CATEGORIES:
                if bots_map[bot_name]['prop'][bot_cat] > 0:
                    project_dict[BOT_REVS_PREFIX.format(bot_cat, 'prop')][idx] += \
                        bots_map[bot_name]['prop'][bot_cat]

    return project_dict

# ---------------------------------------------------------------------------
# Variable computation: article page (aggregated per project)
# ---------------------------------------------------------------------------

def compute_article_page_variables(id, project_dict, bots_map, bot_cat_voting_rule_lists):
    article_path = get_article_path(id, ARTICLE_PAGE_REV_DIR)
    if id == -1 or not article_path.exists():
        return project_dict

    article_rev = pd.read_csv(article_path, lineterminator='\n', usecols=ARTICLE_PAGE_REV_COLS)
    article_rev = standardize_columns(article_rev)
    article_rev[YEAR_MONTH_NAME] = (
        pd.to_datetime(article_rev['timestamp'], format='mixed')
        .dt.strftime(YEAR_MONTH_CODE)
    )
    article_rev = article_rev[article_rev[YEAR_MONTH_NAME] < '2024-01']

    for enum_idx, (year_month, group) in enumerate(
        article_rev.groupby(YEAR_MONTH_NAME, as_index=False, sort=False)
    ):
        idx = get_index_from_year_month(year_month)
        if enum_idx == 0:
            for i in range(idx, NUM_MONTHS):
                project_dict['project_size'][i] += 1

        project_dict['num_revs'][idx] += len(group)

        group_human = group[~group['user'].isin(bots_map)]
        project_dict['num_revs_human'][idx] += len(group_human)

        group_bot_all = group[group['user'].isin(bots_map)]
        project_dict['num_revs_bot_all'][idx] += len(group_bot_all)

        for bot_cat in BOT_CATEGORIES:
            for vote in VOTING_RULES:
                if vote == 'prop':
                    continue
                subset = group[group['user'].isin(bot_cat_voting_rule_lists['{}_{}'.format(bot_cat, vote)])]
                project_dict[BOT_REVS_PREFIX.format(bot_cat, vote)][idx] += len(subset)

        for _, bot_rev in group_bot_all.iterrows():
            bot_name = bot_rev['user']
            for bot_cat in BOT_CATEGORIES:
                if bots_map[bot_name]['prop'][bot_cat] > 0:
                    project_dict[BOT_REVS_PREFIX.format(bot_cat, 'prop')][idx] += \
                        bots_map[bot_name]['prop'][bot_cat]

    return project_dict

# ---------------------------------------------------------------------------
# Variable computation: article talk (aggregated per project)
# ---------------------------------------------------------------------------

def compute_article_talk_variables(id, project_dict, bots_map, bot_cat_voting_rule_lists):
    article_path = get_article_path(id, ARTICLE_TALK_REV_DIR)
    if id == -1 or not article_path.exists():
        return project_dict

    article_rev = pd.read_csv(article_path, lineterminator='\n', usecols=ARTICLE_TALK_REV_COLS)
    article_rev = standardize_columns(article_rev)
    article_rev[YEAR_MONTH_NAME] = (
        pd.to_datetime(article_rev['timestamp'], format='mixed')
        .dt.strftime(YEAR_MONTH_CODE)
    )
    article_rev = article_rev[article_rev[YEAR_MONTH_NAME] < '2024-01']

    assessment_history = [None] * NUM_MONTHS
    for _, (year_month, group) in enumerate(
        article_rev.groupby(YEAR_MONTH_NAME, as_index=False, sort=False)
    ):
        idx = get_index_from_year_month(year_month)

        project_dict['num_revs'][idx] += len(group)

        group_human = group[~group['user'].isin(bots_map)]
        project_dict['num_revs_human'][idx] += len(group_human)

        group_bot_all = group[group['user'].isin(bots_map)]
        project_dict['num_revs_bot_all'][idx] += len(group_bot_all)

        for bot_cat in BOT_CATEGORIES:
            for vote in VOTING_RULES:
                if vote == 'prop':
                    continue
                subset = group[group['user'].isin(bot_cat_voting_rule_lists['{}_{}'.format(bot_cat, vote)])]
                project_dict[BOT_REVS_PREFIX.format(bot_cat, vote)][idx] += len(subset)

        for _, bot_rev in group_bot_all.iterrows():
            bot_name = bot_rev['user']
            for bot_cat in BOT_CATEGORIES:
                if bots_map[bot_name]['prop'][bot_cat] > 0:
                    project_dict[BOT_REVS_PREFIX.format(bot_cat, 'prop')][idx] += \
                        bots_map[bot_name]['prop'][bot_cat]

        assessment = compute_page_assessment(group.iloc[-1]['assessment'])
        if assessment is not None:
            for i in range(idx, NUM_MONTHS):
                assessment_history[i] = assessment

    for i, assessment in enumerate(assessment_history):
        if assessment is not None:
            project_dict['num_rated_{}'.format(assessment)][i] += 1

    return project_dict
