"""
Data collection pipeline — Human Coordination Shapes the Promise and
Limits of Autonomous Agents.

Runs all collection stages in order:
  01_download_revisions.py             — download revision histories from Wikipedia API
  02_compute_project_variables.py      — compute project page/talk variables
  03_compute_article_page_variables.py — compute article page variables
  04_compute_article_talk_variables.py — compute article talk variables
  05_assemble_dataset.py               — assemble final panel CSV

Usage:
  python run_data_processing.py           # demo mode (default, recommended)
  python run_data_processing.py --full    # full mode (WARNING: see below)

================================================================================
  DEMO MODE (default)
  Processes the 1 smallest WikiProject (~10 articles).
  Expected runtime: ~2 minutes on a standard laptop.
  Produces a small version of the panel dataset (288 rows × 367 columns)
  for verifying that the pipeline runs correctly end-to-end.
================================================================================

================================================================================
  FULL MODE  (--full flag required)
  Processes all 763 WikiProjects and ~5 million articles.

  *** NOT RECOMMENDED without access to a compute cluster or server. ***

  Expected runtime: several days on a laptop.
  Disk space required: ~500 GB for raw revision histories.

  This is how the original dataset was produced, using a high-performance
  computing cluster (SLURM) with dozens of parallel workers. Running it locally
  will produce identical results but will take much longer.
================================================================================
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR   = Path(__file__).resolve().parent
SCRIPTS    = ROOT_DIR / 'scripts'
PYTHON_EXE = sys.executable


def run(script_name, extra_args=None):
    cmd = [PYTHON_EXE, str(SCRIPTS / script_name)] + (extra_args or [])
    print(f'\n{"=" * 60}')
    print(f'Running: {" ".join(cmd)}')
    print('=' * 60)
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if result.returncode != 0:
        print(f'\nERROR: {script_name} exited with code {result.returncode}. Stopping.')
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(
        description='Run the full data collection and variable computation pipeline.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--full', action='store_true',
        help=(
            'Run on all 763 WikiProjects instead of the 1-project demo. '
            'NOT RECOMMENDED without a compute cluster — expect several days of runtime.'
        ),
    )
    parser.add_argument(
        '--skip-download', action='store_true',
        help='Skip Stage 01 (download). Use if revision histories are already downloaded.',
    )
    parser.add_argument(
        '--date', default=None,
        help='Version date string for the output CSV filename (e.g. 03_22_2026).',
    )
    args = parser.parse_args()

    mode_flag = ['--full'] if args.full else []

    if args.full:
        print()
        print('!' * 70)
        print('!  WARNING: --full mode selected.')
        print('!')
        print('!  This will download ~5 million Wikipedia pages and compute')
        print('!  variables for 763 WikiProjects. It requires:')
        print('!')
        print('!    - A stable internet connection')
        print('!    - ~500 GB of free disk space')
        print('!    - Several days of compute time on a standard laptop')
        print('!')
        print('!  For a quick end-to-end check, run without --full.')
        print('!')
        print('!' * 70)
        confirm = input('\nType YES to continue with full mode: ').strip()
        if confirm != 'YES':
            print('Aborted.')
            sys.exit(0)
    else:
        print()
        print('=' * 60)
        print('Running in DEMO mode (1 smallest WikiProject).')
        print('Pass --full to process all 763 WikiProjects.')
        print('=' * 60)

    if not args.skip_download:
        run('01_download_revisions.py', mode_flag)

    run('02_compute_project_variables.py', mode_flag)
    run('03_compute_article_page_variables.py', mode_flag)
    run('04_compute_article_talk_variables.py', mode_flag)

    date_args = ['--date', args.date] if args.date else []
    run('05_assemble_dataset.py', mode_flag + date_args)

    print('\nCollection pipeline complete.')


if __name__ == '__main__':
    main()
