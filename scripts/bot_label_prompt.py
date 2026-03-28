"""
Bot categorization prompt templates and category descriptions.

Shared by bot_sample_label_llm.py and bot_full_label_llm.py.
Contains the exact system/user prompts and categorization table used in the paper.
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Bot category descriptions (as used in all LLM annotation requests)
# ---------------------------------------------------------------------------

CATEGORIZATION_TABLE = '''
| Category Label | Category Description |
| -------------- | -------------------- |
| Operational | Operational work refers to work that directly translates into the organization's output (i.e., the product, service, or content it generates). On Wikipedia, operational bots primarily make changes to the content of Wikipedia article pages. These bots may inform human editors of the edits they have made, but they typically do not tell human editors what to do. Example tasks include, but are not limited to, bots that make updates to and fix errors in content, links, templates, or files, bots that clean up the formatting or content of an article page, or bots that add redirects or references. |
| Interwiki | On Wikipedia, interwiki links are a special feature on article pages that link topically-equivalent articles across different language versions of Wikipedia together. For example, an article on English Wikipedia about a large city may contain an interwiki link to the French Wikipedia article on the same city. On Wikipedia, interwiki bots fulfill tasks that relate to creating, adjusting, or fixing interwiki links. |
| Task allocation | Task allocation refers to the problem of mapping tasks to individuals and groups. On Wikipedia, task allocation bots may specifically give tasks to individual human editors or a group of editors who are members of a WikiProject. Pay attention to specific mentions of WikiProjects or specific members of Wikipedia as a sign of belonging to this category. Examples include, but are not limited to, bots that flag an article as being part of a specific WikiProject, or bots that mention or notify people or groups, particularly those belonging to a specific WikiProject, that they should work on a certain article page or set of pages. |
| Task division | Task division refers to the problem of mapping the goals of an organization or group into tasks and subtasks. On Wikipedia, task division bots may determine how human editors who are members of a WikiProject should divide their responsibilities. Examples include, but are not limited to, bots that flag articles as having a certain level of quality or priority level to make specific WikiProjects aware of the further work that needs to be done on them, or bots that create new article pages. |
| Information provision | The provision of information refers to the problem of ensuring that an organization\'s members have the information needed to execute their tasks and coordinate actions with others. On Wikipedia, information provision bots provide human editors with some information (e.g., on an article talk page, a WikiProject page, a WikiProject talk page, etc.) that may help them do work or collaborate more effectively with other editors. Examples include, but are not limited to, bots that contribute to article talk page discussions, bots that gather, summarize, and archive files, images, and discussions in one place, bots that generate and update various statistics, tables, and charts which summarize activity, events, or content, or bots that either notify users or mark specific users with some information. |
| Reward provision | The provision of rewards refers to the problem of allocating a set of rewards to the members of an organization in order to motivate them to execute tasks. On Wikipedia, reward provision bots may perform tasks that award and recognize human editors for their efforts. Examples include, but are not limited to, bots that attribute "barn stars", a Wikipedia award type, to editors for their past contributions. |
| Exception management | Exception management refers to the problem of resolving disputes and correcting errors when they arise. On Wikipedia, exception management bots may perform tasks which are meant to reduce unproductive edits or legal issues. Unproductive edits may include "edit wars" whereby humans successively erase each other\'s edits, or "vandalism" whereby humans intentionally make edits that are disruptive and malicious. Examples include, but are not limited to, bots that detect, log, or revert acts of spam and vandalism, bots that warn or block vandalizing editors, or bots that check for copyright issues in files and images. |
| Other | Bots which perform tasks that are not clear or do not fit into any of the above categories will be classified as "Other". This can be because the functions are different from and do not match up well with the above categories and their descriptions, or because the bot\'s function description is unclear or insufficiently detailed to determine whether it fits into one of the above categories. |
'''

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = '''
## Context
You are a helpful research assistant. You have been employed to help on a research project studying the effects of collaboration between human editors and bots on Wikipedia.

## Task Overview
Your task is to assign bots to different categories based on their specific functions and activities, using the provided categorization table. For each bot that you will label, you will be provided a description of their functionality written by the bot\'s creator.

## Categorization Table
{}

## Guidelines and Tips
### General Process
- **Step 1**: For each bot, read the provided function description carefully. For the function description, focus on the parts that describe the bot\'s primary purpose and main editing activities. Note that in some cases, not all information in the description will be relevant for categorization (e.g., some technical details and implementation specifics such as programming language used to write the bot are irrelevant).
- **Step 2**: Compare the function description information in Step 1 with the category labels and descriptions in the categorization table.
- **Step 3**: Select the category that best matches the bot\'s primary function.

### How to Handle Difficult Cases
- **Multiple bot functions**: For bots which appear to have multiple, distinct functions, assign a category based on your best judgment of the primary or dominant function of the bot. For bots that engage in what seems to be a complicated sequence of activities in order to achieve some broader purpose or goal, do your best to assign the most relevant category based on the overall purpose of the bot, and not any specific lower-level activity.
- **Missing, unclear, or ambiguous information**: Bot creators vary in their writing of the function description in terms of completeness, formatting, and relevance. Do your best to understand the core of what each bot is doing despite this variation. For bots with function descriptions that are extremely lacking in relevant information or extremely ambiguous, prefer to assign the catch-all **Other** category rather than infer a more specific category.
'''

USER_PROMPT = '''
## Bot Function Description
{}

## Response
Please respond with the category label from the categorization table that best matches the bot\'s function description, keeping in mind the provided guidelines and tips.
'''

# ---------------------------------------------------------------------------
# Helper: build function description string from a BotCombined row
# ---------------------------------------------------------------------------

def create_bot_description(row) -> str:
    """
    Construct the input text for LLM categorization from a row of the
    quarry_scraped_botlist_combined CSV. Prioritizes structured fields
    (func_overview + func_details) over the raw bot user page content.
    """
    if not pd.isna(row['func_overview']) and not pd.isna(row['func_details']):
        return '### Summary:\n{}\n\n### Details:\n{}\n'.format(
            row['func_overview'], row['func_details'])
    elif not pd.isna(row['func_overview']):
        return '### Summary:\n{}\n'.format(row['func_overview'])
    elif not pd.isna(row['func_details']):
        return '### Details:\n{}\n'.format(row['func_details'])
    else:
        return '{}\n'.format(row['bot_user_page_content'])
