"""
Stage 10: Download revision histories from the Wikipedia MediaWiki API.

Demo mode (default): downloads histories for the 10 smallest WikiProjects only
  (~hundreds to low-thousands of articles, completes in minutes to hours).
Full mode (--full):  downloads histories for all 763 WikiProjects
  (~5 million articles; expect 24–48 hours on a laptop).

Usage:
  python scripts/01_download_revisions.py            # demo
  python scripts/01_download_revisions.py --full     # full (see warning below)

Outputs (written to raw/):
  raw/project/<project_id>_revision_history.csv
  raw/project_talk/<project_talk_id>_revision_history.csv
  raw/article/<bucket>/<article_id>_revision_history.csv
  raw/article_talk/<bucket>/<article_talk_id>_revision_history.csv

where <bucket> is the 10k-bucket folder, e.g. 38790000_38799999.
"""

import argparse
import multiprocessing as mp
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

# Add scripts/ to path so collection_utils can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collection_utils import (
    PROJECT_PAGE_REV_DIR, PROJECT_TALK_REV_DIR,
    ARTICLE_PAGE_REV_DIR, ARTICLE_TALK_REV_DIR,
    ALL_ARTICLE_INFO_FILE,
    get_ordered_project_sample_df,
)

# ---------------------------------------------------------------------------
# API constants
# ---------------------------------------------------------------------------

BASE_API_URL    = 'https://en.wikipedia.org/w/api.php'
MAX_RETRIES     = 3
RETRY_DELAY_S   = 3
TIMEOUT_S       = 120
SUCCESS_CODE    = 200

# ---------------------------------------------------------------------------
# User-Agent header — required by Wikimedia API etiquette.
# See: https://www.mediawiki.org/wiki/API:Main_page#Identifying_your_client
#
# Replace YOUR_NAME and YOUR_EMAIL below with your own name and email address
# before running this script.
# ---------------------------------------------------------------------------
_CONTACT = 'YOUR_NAME (YOUR_EMAIL)'

_PAPER   = 'Human Coordination Shapes the Promise and Limits of Autonomous Agents'
HEADERS  = {'User-Agent': f'{_PAPER} — {_CONTACT}'}

BASE_RV_PARAMS = {
    'action':       'query',
    'format':       'json',
    'formatversion':'2',
    'prop':         'revisions',
    'rvstart':      '2000-01-01T00:00:00Z',
    'rvend':        '2024-01-01T00:00:00Z',
    'rvdir':        'newer',
    'rvslots':      '*',
}

_PROJECT_RV_PROPS = [
    'ids', 'flags', 'timestamp', 'user', 'userid', 'size', 'slotsize', 'sha1',
    'slotsha1', 'contentmodel', 'comment', 'parsedcomment', 'content', 'tags', 'roles',
]
_PROJECT_RV_FIELDS = [
    'revid', 'parentid', 'minor', 'user', 'userid', 'timestamp',
    'size', 'sha1', 'comment', 'parsedcomment', 'tags',
]
_PROJECT_RV_SLOTS = ['contentmodel', 'contentformat', 'content']

_ARTICLE_RV_PROPS = [
    'ids', 'flags', 'timestamp', 'user', 'userid', 'size', 'slotsize', 'sha1',
    'slotsha1', 'contentmodel', 'comment', 'parsedcomment', 'tags', 'roles',
]
_ARTICLE_RV_FIELDS = [
    'revid', 'parentid', 'minor', 'user', 'userid', 'timestamp',
    'size', 'sha1', 'comment', 'parsedcomment', 'tags',
]
_ARTICLE_RV_SLOTS = []

_ARTICLE_TALK_RV_PROPS = [
    'ids', 'flags', 'timestamp', 'user', 'userid', 'size', 'slotsize', 'sha1',
    'slotsha1', 'contentmodel', 'comment', 'parsedcomment', 'content', 'tags', 'roles',
]
_ARTICLE_TALK_RV_FIELDS = [
    'revid', 'parentid', 'minor', 'user', 'userid', 'timestamp',
    'size', 'sha1', 'comment', 'parsedcomment', 'tags',
]
_ARTICLE_TALK_RV_SLOTS = ['contentmodel', 'contentformat', 'content']

COMBINED_REGEX = re.compile(
    r'\{\{([^\{\}]*(?:wp|wikiproject|class|importance|priority|rating)[^\{\}]*)'
)

PROJECT_RV_PARAMS       = {**BASE_RV_PARAMS, 'rvlimit': '50',  'rvprop': '|'.join(_PROJECT_RV_PROPS)}
ARTICLE_RV_PARAMS       = {**BASE_RV_PARAMS, 'rvlimit': '500', 'rvprop': '|'.join(_ARTICLE_RV_PROPS)}
ARTICLE_TALK_RV_PARAMS  = {**BASE_RV_PARAMS, 'rvlimit': '50',  'rvprop': '|'.join(_ARTICLE_TALK_RV_PROPS)}


def _get_rv_options(page_type):
    if page_type in ('project', 'project_talk'):
        return str(PROJECT_PAGE_REV_DIR if page_type == 'project' else PROJECT_TALK_REV_DIR), \
               PROJECT_RV_PARAMS, _PROJECT_RV_FIELDS, _PROJECT_RV_SLOTS
    elif page_type == 'article':
        return str(ARTICLE_PAGE_REV_DIR), ARTICLE_RV_PARAMS, _ARTICLE_RV_FIELDS, _ARTICLE_RV_SLOTS
    elif page_type == 'article_talk':
        return str(ARTICLE_TALK_REV_DIR), ARTICLE_TALK_RV_PARAMS, _ARTICLE_TALK_RV_FIELDS, _ARTICLE_TALK_RV_SLOTS


def _get_file_path(page_id, page_type, directory):
    file_name = f'{page_id}_revision_history.csv'
    if page_type in ('project', 'project_talk'):
        return None, os.path.join(directory, file_name)
    else:
        lower = (page_id // 10000) * 10000
        upper = lower + 9999
        folder = os.path.join(directory, f'{lower}_{upper}')
        return folder, os.path.join(folder, file_name)


def _get_revision_history(page_id, page_type):
    directory, rv_params, rv_fields, rv_slots = _get_rv_options(page_type)
    revision_history = []
    continue_val = ''

    while True:
        params = rv_params.copy()
        params['pageids'] = page_id
        if continue_val:
            params['rvcontinue'] = continue_val

        api_response = None
        for _ in range(MAX_RETRIES):
            try:
                api_response = requests.post(
                    BASE_API_URL, headers=HEADERS, data=params, timeout=TIMEOUT_S
                )
                if api_response.status_code == SUCCESS_CODE:
                    break
                time.sleep(RETRY_DELAY_S)
            except requests.exceptions.RequestException:
                time.sleep(RETRY_DELAY_S)

        if api_response is None or api_response.status_code != SUCCESS_CODE:
            return None

        response = api_response.json()
        page = response['query']['pages'][0]
        if page.get('missing') or 'revisions' not in page:
            return None

        for revision in page['revisions']:
            rev_data = {
                'pageid': page['pageid'],
                'ns':     page['ns'],
                'title':  page['title'],
            }
            for field in rv_fields:
                if field in revision:
                    rev_data[field] = revision[field]

            if 'slots' in revision and 'main' in revision['slots']:
                slot = revision['slots']['main']
                for field in rv_slots:
                    if field not in slot:
                        continue
                    if field == 'content':
                        curr_content = slot['content']
                        if page_type in ('project', 'project_talk'):
                            rev_data['content'] = curr_content
                        if page_type == 'article_talk':
                            text = curr_content.replace('\n', '').lower()
                            rev_data['assessment'] = re.findall(COMBINED_REGEX, text)
                    else:
                        rev_data[field] = slot[field]

            revision_history.append(rev_data)

        if 'continue' in response:
            continue_val = response['continue']['rvcontinue']
        else:
            break

    return pd.DataFrame(revision_history)


def _download_and_save(id_type_pair):
    page_id, page_type = id_type_pair
    if page_id == -1:
        return
    directory, _, _, _ = _get_rv_options(page_type)
    folder_path, file_path = _get_file_path(page_id, page_type, directory)
    if os.path.exists(file_path):
        return
    if folder_path is not None:
        os.makedirs(folder_path, exist_ok=True)
    df = _get_revision_history(page_id, page_type)
    if df is not None:
        df.to_csv(file_path, encoding='utf-8', index=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

DEMO_N = 1  # number of smallest WikiProjects to use in demo mode


def main():
    parser = argparse.ArgumentParser(
        description='Download Wikipedia revision histories.'
    )
    parser.add_argument(
        '--full', action='store_true',
        help='Run on all 763 WikiProjects instead of the demo subset.'
    )
    args = parser.parse_args()
    demo = not args.full

    if args.full:
        print('=' * 70)
        print('WARNING: --full mode selected.')
        print('This will download revision histories for ~763 WikiProjects')
        print('and ~5 million articles/talk pages.')
        print('Expected runtime: 24-48 hours on a laptop.')
        print('Ensure a stable internet connection and sufficient disk space')
        print('(several hundred GB).')
        print('=' * 70)
        confirm = input('Type YES to continue: ').strip()
        if confirm != 'YES':
            print('Aborted.')
            sys.exit(0)

    # Create output directories
    for d in [PROJECT_PAGE_REV_DIR, PROJECT_TALK_REV_DIR,
              ARTICLE_PAGE_REV_DIR, ARTICLE_TALK_REV_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # Load metadata
    print('Loading metadata CSV (this may take 1-2 minutes)...')
    source = pd.read_csv(ALL_ARTICLE_INFO_FILE)
    project_to_articles_df = get_ordered_project_sample_df(source)

    if demo:
        project_to_articles_df = project_to_articles_df.iloc[:DEMO_N]
        print(f'Demo mode: processing {DEMO_N} smallest WikiProjects.')
        article_ids = set()
        article_talk_ids = set()
        for _, row in project_to_articles_df.iterrows():
            article_ids.update(row['member_article_ids'])
            article_talk_ids.update(row['member_article_talk_ids'])
        article_ids = list(article_ids)
        article_talk_ids = list(article_talk_ids)
        num_processes = 1
    else:
        article_ids = source['corresponding_page_id'].unique().tolist()
        article_talk_ids = source['page_id'].unique().tolist()
        num_processes = max(1, mp.cpu_count() - 2)
        print(f'Full mode: {len(project_to_articles_df)} WikiProjects, '
              f'{len(article_ids)} articles, using {num_processes} processes.')

    project_ids      = project_to_articles_df['project_page_id'].tolist()
    project_talk_ids = project_to_articles_df['project_talk_id'].tolist()

    # --- Stage A: project pages (sequential, only 763 total) ---
    print(f'\n[Stage A] Downloading {len(project_ids)} project page revision histories...')
    for pid in tqdm(project_ids):
        _download_and_save((pid, 'project'))

    # --- Stage B: project talk pages ---
    print(f'\n[Stage B] Downloading {len(project_talk_ids)} project talk revision histories...')
    if num_processes == 1:
        for ptid in tqdm(project_talk_ids):
            _download_and_save((ptid, 'project_talk'))
    else:
        with mp.Pool(processes=num_processes) as pool:
            pairs = list(zip(project_talk_ids, ['project_talk'] * len(project_talk_ids)))
            for _ in tqdm(pool.imap_unordered(_download_and_save, pairs),
                          total=len(pairs)):
                pass

    # --- Stage C: article pages ---
    print(f'\n[Stage C] Downloading {len(article_ids)} article revision histories...')
    if num_processes == 1:
        for aid in tqdm(article_ids):
            _download_and_save((aid, 'article'))
    else:
        with mp.Pool(processes=num_processes) as pool:
            pairs = list(zip(article_ids, ['article'] * len(article_ids)))
            for _ in tqdm(pool.imap_unordered(_download_and_save, pairs),
                          total=len(pairs)):
                pass

    # --- Stage D: article talk pages ---
    print(f'\n[Stage D] Downloading {len(article_talk_ids)} article talk revision histories...')
    if num_processes == 1:
        for atid in tqdm(article_talk_ids):
            _download_and_save((atid, 'article_talk'))
    else:
        with mp.Pool(processes=num_processes) as pool:
            pairs = list(zip(article_talk_ids, ['article_talk'] * len(article_talk_ids)))
            for _ in tqdm(pool.imap_unordered(_download_and_save, pairs),
                          total=len(pairs)):
                pass

    print('\nDownload complete.')


if __name__ == '__main__':
    main()
