"""
Bot Categorization — GPT-4o Labeling of All 4,932 Bot Tasks.

Calls the OpenAI API (gpt-4o-2024-11-20) to assign a category label to each
bot task in the full dataset. This produced the file
data/Full_4932_LLMLabel_gpt-4o-2024-11-20.csv used in the paper.

gpt-4o-2024-11-20 was selected as the labeling model based on accuracy metrics
computed by bot_label_evaluation.py on the 120-bot evaluation sample.

Usage:
    python scripts/bot_full_label_llm.py

API key is read from the OPENAI_API_KEY environment variable.

Input:  data/quarry_scraped_botlist_combined.csv
Output: data/Full_{n}_LLMLabel_gpt-4o-2024-11-20.csv

Note: running this script costs approximately $5-10 USD in OpenAI API credits
and takes roughly 1-2 hours. The output file is already included in data/.
"""

import os
import sys
import time
from pathlib import Path

import pandas as pd
from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_random_exponential

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bot_label_prompt

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / 'data'

BOT_COMBINED_FILE = DATA_DIR / 'quarry_scraped_botlist_combined.csv'
MODEL_NAME        = 'gpt-4o-2024-11-20'
INTERMEDIATE_SAVE_EVERY = 50   # save a checkpoint every N rows


class BotCategory(BaseModel):
    categoryLabel: str


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(5))
def categorize(client, messages):
    return client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=messages,
        response_format=BotCategory,
        temperature=0.0,
        seed=1,
    )


def main():
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    print(f'Loading bot data from {BOT_COMBINED_FILE.name}...')
    df = pd.read_csv(BOT_COMBINED_FILE)

    # Exclude rows missing all forms of function description
    df = df[~(
        df['func_overview'].isna() &
        df['func_details'].isna() &
        df['bot_user_page_content'].isna()
    )].reset_index(drop=True)
    print(f'Bots with at least one function description: {len(df)}')

    labels = []
    start = time.time()

    for idx, row in df.iterrows():
        description = bot_label_prompt.create_bot_description(row)
        messages = [
            {'role': 'system', 'content': bot_label_prompt.SYSTEM_PROMPT.format(bot_label_prompt.CATEGORIZATION_TABLE)},
            {'role': 'user',   'content': bot_label_prompt.USER_PROMPT.format(description)},
        ]
        result = categorize(client, messages)
        labels.append(result.choices[0].message.parsed.categoryLabel)

        if (idx + 1) % 10 == 0:
            print(f'  [{idx + 1}/{len(df)}] elapsed: {time.time() - start:.0f}s')

        # Save intermediate checkpoint every INTERMEDIATE_SAVE_EVERY rows
        if idx > 0 and (idx + 1) % INTERMEDIATE_SAVE_EVERY == 0:
            chk = pd.DataFrame({
                'Bot Index': range(idx + 1),
                'Bot Task':  df['bot_task'][:idx + 1].values,
                'Bot':       df['bot'][:idx + 1].values,
                MODEL_NAME:  labels,
            })
            chk_path = DATA_DIR / f'Full_{len(df)}_LLMLabel_{MODEL_NAME}_intermediate.csv'
            chk.to_csv(chk_path, index=False)
            print(f'  Checkpoint saved to {chk_path.name}')

    print(f'Finished. Total time: {time.time() - start:.0f}s')

    out_df = pd.DataFrame({
        'Bot Index': range(len(df)),
        'Bot Task':  df['bot_task'].values,
        'Bot':       df['bot'].values,
        MODEL_NAME:  labels,
    })
    out_path = DATA_DIR / f'Full_{len(df)}_LLMLabel_{MODEL_NAME}.csv'
    out_df.to_csv(out_path, index=False)
    print(f'Saved to {out_path.relative_to(ROOT_DIR)}')


if __name__ == '__main__':
    main()
