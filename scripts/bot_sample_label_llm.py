"""
Bot Categorization — LLM Labeling on 120-Bot Evaluation Sample.

Draws the same 120-bot random sample (random_state=1) used in the paper,
calls the specified LLM API to assign a category label to each bot task,
and writes the results to data/.

This script was used to generate the per-model label files that feed into
bot_label_evaluation.py. It was run once per model during the iterative
prompt-refinement phase described in Appendix §Bot Category Annotation Procedure.

Usage:
    python scripts/bot_sample_label_llm.py --model gpt-4o-2024-11-20
    python scripts/bot_sample_label_llm.py --model gpt-4o-mini-2024-07-18
    python scripts/bot_sample_label_llm.py --model claude-3-5-sonnet-20241022
    python scripts/bot_sample_label_llm.py --model gemini-1.5-pro-002

API keys are read from environment variables:
    OPENAI_API_KEY       (required for gpt-4o-* and gpt-4o-mini-* models)
    ANTHROPIC_API_KEY    (required for claude-* models)
    GOOGLE_API_KEY       (required for gemini-* models)

Input:  data/quarry_scraped_botlist_combined.csv
Output: data/BotCat_LLMLabel_{model}_120.csv
"""

import argparse
import enum
import os
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bot_label_prompt

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / 'data'

BOT_COMBINED_FILE = DATA_DIR / 'quarry_scraped_botlist_combined.csv'

SAMPLE_SIZE   = 120
RANDOM_STATE  = 1


def load_sample(bot_combined_file: Path) -> pd.DataFrame:
    """Load the BotCombined CSV, exclude rows missing all function text, and draw the 120-bot sample."""
    df = pd.read_csv(bot_combined_file)
    df = df[~(
        df['func_overview'].isna() &
        df['func_details'].isna() &
        df['bot_user_page_content'].isna()
    )].reset_index(drop=True)
    return df.sample(n=SAMPLE_SIZE, random_state=RANDOM_STATE).reset_index(drop=True)


# ---------------------------------------------------------------------------
# OpenAI (gpt-4o-*, gpt-4o-mini-*)
# ---------------------------------------------------------------------------

def run_openai(sample_df: pd.DataFrame, model_name: str) -> list[str]:
    from openai import OpenAI
    from pydantic import BaseModel
    from tenacity import retry, stop_after_attempt, wait_random_exponential

    class BotCategory(BaseModel):
        categoryLabel: str

    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(5))
    def categorize(messages):
        return client.beta.chat.completions.parse(
            model=model_name,
            messages=messages,
            response_format=BotCategory,
            temperature=0.0,
            seed=1,
        )

    labels = []
    start = time.time()
    for idx, row in sample_df.iterrows():
        description = bot_label_prompt.create_bot_description(row)
        messages = [
            {'role': 'system', 'content': bot_label_prompt.SYSTEM_PROMPT.format(bot_label_prompt.CATEGORIZATION_TABLE)},
            {'role': 'user',   'content': bot_label_prompt.USER_PROMPT.format(description)},
        ]
        result = categorize(messages)
        labels.append(result.choices[0].message.parsed.categoryLabel)
        if (idx + 1) % 10 == 0:
            print(f'  [{idx + 1}/{len(sample_df)}] elapsed: {time.time() - start:.0f}s')
    return labels


# ---------------------------------------------------------------------------
# Anthropic (claude-*)
# ---------------------------------------------------------------------------

def run_anthropic(sample_df: pd.DataFrame, model_name: str) -> list[str]:
    import anthropic
    import instructor
    from pydantic import BaseModel

    class BotCategory(BaseModel):
        categoryLabel: str

    client = instructor.from_anthropic(anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY']))

    labels = []
    start = time.time()
    for idx, row in sample_df.iterrows():
        description = bot_label_prompt.create_bot_description(row)
        system = [{
            'type': 'text',
            'text': bot_label_prompt.SYSTEM_PROMPT.format(bot_label_prompt.CATEGORIZATION_TABLE),
            'cache_control': {'type': 'ephemeral'},
        }]
        messages = [{'role': 'user', 'content': bot_label_prompt.USER_PROMPT.format(description)}]
        result = client.messages.create(
            model=model_name,
            max_tokens=128,
            system=system,
            messages=messages,
            response_model=BotCategory,
            temperature=0.0,
        )
        labels.append(result.categoryLabel)
        if (idx + 1) % 10 == 0:
            print(f'  [{idx + 1}/{len(sample_df)}] elapsed: {time.time() - start:.0f}s')
    return labels


# ---------------------------------------------------------------------------
# Google (gemini-*)
# ---------------------------------------------------------------------------

def run_google(sample_df: pd.DataFrame, model_name: str) -> list[str]:
    import datetime as _dt
    import google.generativeai as genai
    from google.generativeai import caching

    class BotCategory(enum.Enum):
        OPERATIONAL         = 'Operational'
        INTERWIKI           = 'Interwiki'
        TASK_ALLOCATION     = 'Task allocation'
        TASK_DIVISION       = 'Task division'
        INFORMATION_PROVISION = 'Information provision'
        REWARD_PROVISION    = 'Reward provision'
        EXCEPTION_MANAGEMENT = 'Exception management'
        OTHER               = 'Other'

    genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
    cache = caching.CachedContent.create(
        model='models/' + model_name,
        display_name='wiki-bots',
        system_instruction=bot_label_prompt.SYSTEM_PROMPT.format(bot_label_prompt.CATEGORIZATION_TABLE),
        ttl=_dt.timedelta(minutes=30),
    )
    model = genai.GenerativeModel.from_cached_content(cached_content=cache)

    labels = []
    start = time.time()
    for idx, row in sample_df.iterrows():
        description = bot_label_prompt.create_bot_description(row)
        response = model.generate_content(
            bot_label_prompt.USER_PROMPT.format(description),
            generation_config=genai.GenerationConfig(
                max_output_tokens=128,
                temperature=0.0,
                response_mime_type='text/x.enum',
                response_schema=BotCategory,
            ),
        )
        labels.append(response.text)
        if (idx + 1) % 10 == 0:
            print(f'  [{idx + 1}/{len(sample_df)}] elapsed: {time.time() - start:.0f}s')
    return labels


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Categorize the 120-bot evaluation sample using an LLM.')
    parser.add_argument(
        '--model', required=True,
        choices=['gpt-4o-2024-11-20', 'gpt-4o-mini-2024-07-18',
                 'claude-3-5-sonnet-20241022', 'gemini-1.5-pro-002'],
        help='LLM model to use for categorization.',
    )
    args = parser.parse_args()

    print(f'Loading bot sample from {BOT_COMBINED_FILE.name}...')
    sample_df = load_sample(BOT_COMBINED_FILE)
    print(f'Sample size: {len(sample_df)} bots')

    print(f'Running categorization with {args.model}...')
    if args.model.startswith('gpt'):
        labels = run_openai(sample_df, args.model)
    elif args.model.startswith('claude'):
        labels = run_anthropic(sample_df, args.model)
    elif args.model.startswith('gemini'):
        labels = run_google(sample_df, args.model)
    else:
        raise ValueError(f'Unknown model: {args.model}')

    out_file = DATA_DIR / f'BotCat_LLMLabel_{args.model}_{SAMPLE_SIZE}.csv'
    out_df = pd.DataFrame({
        'Bot Index': range(len(sample_df)),
        'Bot Task':  sample_df['bot_task'].values,
        'Bot':       sample_df['bot'].values,
        args.model:  labels,
    })
    out_df.to_csv(out_file, index=False)
    print(f'Saved to {out_file.relative_to(ROOT_DIR)}')


if __name__ == '__main__':
    main()
