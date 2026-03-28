"""
Bot Categorization — LLM Accuracy Evaluation.

Evaluates the categorization accuracy of each LLM (and their majority vote)
against expert human labels on the 120-bot evaluation sample.

Reproduces the accuracy results reported in Appendix §Bot Category Annotation
Procedure.  Four models were evaluated: gpt-4o-2024-11-20, gpt-4o-mini-2024-07-18,
claude-3-5-sonnet-20241022, and gemini-1.5-pro-002.  gpt-4o-2024-11-20 achieved
the highest accuracy on the human-labeled subset and was therefore selected for
the full-dataset categorization.

Usage:
    python scripts/bot_label_evaluation.py

Input:  data/BotCat_AllLabels_120.csv
Output: printed to stdout
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

ROOT_DIR  = Path(__file__).resolve().parent.parent
DATA_DIR  = ROOT_DIR / 'data'

ALL_LABELS_FILE = DATA_DIR / 'BotCat_AllLabels_120.csv'

# Models present in the majority file (in paper order)
LLM_MODELS = [
    'gpt-4o-2024-11-20',
    'gpt-4o-mini-2024-07-18',
    'claude-3-5-sonnet-20241022',
    'gemini-1.5-pro-002',
]
MAJORITY_COL  = 'LLM Majority'
HUMAN_COL     = 'Human Label'

# Canonical category order for confusion matrices / categorization reports
CATEGORIES = [
    'Operational',
    'Interwiki',
    'Task allocation',
    'Task division',
    'Information provision',
    'Reward provision',
    'Exception management',
    'Other',
]


def banner(text: str) -> None:
    print(f'\n{"=" * 70}')
    print(f'  {text}')
    print('=' * 70)


def evaluate_model(y_true: pd.Series, y_pred: pd.Series, model_label: str) -> None:
    """Print accuracy, macro/micro F1, per-class report, and confusion matrix."""
    banner(model_label)
    acc     = accuracy_score(y_true, y_pred)
    macro   = f1_score(y_true, y_pred, average='macro',  zero_division=0)
    micro   = f1_score(y_true, y_pred, average='micro',  zero_division=0)
    print(f'Accuracy   : {acc:.4f}')
    print(f'Macro  F1  : {macro:.4f}')
    print(f'Micro  F1  : {micro:.4f}')

    print('\nCategorization Report:')
    present = sorted(set(y_true) | set(y_pred))
    print(classification_report(y_true, y_pred, labels=present, zero_division=0))

    print('Confusion Matrix (rows = true, cols = predicted):')
    cm = confusion_matrix(y_true, y_pred, labels=present)
    # Pretty-print with labels
    col_width = max(len(c) for c in present) + 2
    header = ' ' * col_width + ''.join(c.ljust(col_width) for c in present)
    print(header)
    for label, row in zip(present, cm):
        print(label.ljust(col_width) + ''.join(str(v).ljust(col_width) for v in row))


def main():
    print(f'Loading {ALL_LABELS_FILE.name}...')
    df = pd.read_csv(ALL_LABELS_FILE)

    # Retain only rows that have a human label
    df = df.dropna(subset=[HUMAN_COL]).reset_index(drop=True)
    print(f'Bots with human labels: {len(df)}')

    y_human = df[HUMAN_COL]

    # Label distribution of human annotations
    banner('Human Label Distribution')
    counts = y_human.value_counts()
    for cat, n in counts.items():
        print(f'  {cat:<25} {n:>4}  ({n / len(y_human) * 100:.1f}%)')

    # Evaluate each LLM model
    for model in LLM_MODELS:
        if model not in df.columns:
            print(f'\nSkipping {model} — column not found in file.')
            continue
        evaluate_model(y_human, df[model], model)

    # Evaluate majority vote
    if MAJORITY_COL in df.columns:
        evaluate_model(y_human, df[MAJORITY_COL], f'Majority Vote ({", ".join(LLM_MODELS)})')
    else:
        print(f'\nMajority column "{MAJORITY_COL}" not found — skipping.')

    print('\nEvaluation complete.')


if __name__ == '__main__':
    main()
