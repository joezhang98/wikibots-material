# Code + Data for "Human Coordination Shapes the Promise and Limits of Autonomous Agents"

This repository contains the code and data for reproducing all analyses and results reported in the paper.

There are **two main scripts**:
 
| Script | Purpose |
|--------|---------|
| `run_data_processing.py` | Runs the data collection and processing pipeline: collects and processes all of the raw data components from Wikipedia and combines them into a panel dataset for analysis. This part is not expected/recommended to be run in full (due to raw data size and constraints on storage and computation time), only in demo mode to demonstrate the replicability of the data collection procedure. The final processed dataset is already included in `data/` to be used directly in replicating the analyses. |
| `run_data_analysis.py` | Runs the full data analysis pipeline: prepares the final dataset, runs all descriptive and statistical analyses, and produces every table and figure in the paper. |

---

## Quick Start

```bash
# 1. Install Git LFS (required to download large data files — see Prerequisites)
git lfs install

# 2. Clone the repository
git clone https://github.com/joezhang98/wikibots-material.git
cd wikibots-material

# 3. Create and activate a Python virtual environment
python3 -m venv wikibots-replication-venv
source wikibots-replication-venv/bin/activate          # Windows: wikibots-replication-venv\Scripts\activate.bat

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Run the full analysis pipeline (produces all tables and figures showing statistical results)
python3 run_data_analysis.py
```

> **Stata required.** See [Prerequisites](#prerequisites) for installation details. Stata is auto-detected; set `STATA_EXE` only if it is installed to a non-standard location.

> **Git LFS required.** Three large data files are stored via [Git Large File Storage](https://git-lfs.github.com/). You must install Git LFS and run `git lfs install` before cloning, or the large files will be downloaded as text pointers instead of their actual contents. See [Prerequisites](#prerequisites) for details.

---

## Repository Structure

```
wikibots-material/
├── data/               # all input data files (see Part 1 and Part 2 for details)
├── scripts/            # bot categorization, data collection and processing, and data analysis scripts
├── results/
│   ├── figures/        # output figures (recreated by run_data_analysis.py)
│   └── tables/         # regression tables (recreated by run_data_analysis.py)
├── processed/          # intermediate files created at runtime
├── run_data_analysis.py    # main script for running the end-to-end data analysis pipeline
├── run_data_processing.py  # main script for running the end-to-end data collection and processing pipeline (demo mode recommended)
└── requirements.txt
```

---

## Prerequisites

### Git LFS (required to download large data files)

Three data files are stored in this repository using [Git Large File Storage (LFS)](https://git-lfs.github.com/):

- `data/full_sample_project_level_variables.csv` (~142 MB)
- `data/quarry_project_category_links.csv` (~702 MB)
- `data/all_article_talk_and_project_info_filtered.csv` (~1.2 GB)

**You must install Git LFS before cloning.** Without it, these files will appear as small text pointer files rather than their actual contents.

Install Git LFS:

```bash
# macOS (Homebrew)
brew install git-lfs

# Ubuntu / Debian
sudo apt-get install git-lfs

# Windows — download the installer from https://git-lfs.github.com/
```

Then enable it once for your user account:

```bash
git lfs install
```

After that, a normal `git clone` will automatically fetch all LFS-tracked files.

If you have already cloned without LFS, run `git lfs pull` inside the repository to download the actual file contents.

---

### Python 3.10 or higher

Verify your version:
```bash
python --version
```

### Stata 16 or higher (required for the data analysis pipeline)

The scripts use `frames` (Stata 16+) and the following user-contributed packages, which are **installed automatically on first run** via `ssc install`:

- `reghdfe` — high-dimensional fixed-effects regression
- `ftools` — dependency for `reghdfe`
- `erepost` — dependency of `estfe` (from `reghdfe`)
- `estout` — regression table export (`esttab`, `estpost`, `estfe`)
- `require` — package version management

> **Internet connection required** the first time `run_data_analysis.py` is run, so that Stata can install the packages above.

#### Stata executable path

`run_data_analysis.py` automatically searches common install locations across Stata versions (16–19) and editions (MP, SE, BE/IC), preferring newer versions and more capable editions. It will find Stata regardless of which version or edition you have installed.

If Stata is not found automatically (e.g. installed to a non-standard location), set the `STATA_EXE` environment variable to the full path of your Stata executable before running:

```bash
# macOS / Linux
export STATA_EXE=/path/to/your/stata

# Windows (Command Prompt)
set STATA_EXE=C:\path\to\your\Stata.exe

# Windows (PowerShell)
$env:STATA_EXE = "C:\path\to\your\Stata.exe"
```

---

## Setup

### 1. Install Git LFS and clone the repository

```bash
git lfs install   # run once to enable LFS on your machine
git clone https://github.com/joezhang98/wikibots-material.git
cd wikibots-material
```

### 2. Create a virtual environment

**macOS / Linux**
```bash
python3 -m venv wikibots-replication-venv
source wikibots-replication-venv/bin/activate
```

**Windows (Command Prompt)**
```cmd
python -m venv wikibots-replication-venv
wikibots-replication-venv\Scripts\activate.bat
```

**Windows (PowerShell)**
```powershell
python -m venv wikibots-replication-venv
wikibots-replication-venv\Scripts\Activate.ps1
```

> If you see a permissions error on Windows PowerShell, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 3. Install Python dependencies

With the virtual environment activated:

```bash
pip install -r requirements.txt
```

---

## Part 1 — Bot Categorization Pipeline

> **The final outputs of this pipeline are already included in `data/` and do not need to be regenerated. To reproduce the paper's tables and figures, skip directly to [Part 3](#part-3--reproducing-results-stages-0611).**

The bot categorization pipeline produces the file `data/Full_4932_LLMLabel_gpt-4o-2024-11-20.csv`, which maps each of the 4,932 Wikipedia bot tasks to one of 8 task categories. This file is a required input to the collection pipeline (Part 2).

### Input data files

| File | Description |
|------|-------------|
| `quarry_scraped_botlist_combined.csv` | Bot features dataset: one row per bot task, with scraped function descriptions from Wikipedia bot approval pages and bot user pages. This file was collected and assembled by the Stanford Data Analytics, Research, and Computing (DARC) team on behalf of the authors. Function description text was extracted from bot approval page content using regex patterns. |
| `BotCat_HumanLabels_120.csv` | Human labels (from the author team) for 120 bot tasks randomly sampled from the full 4,932. |
| `BotCat_LLMLabel_gpt-4o-2024-11-20_120.csv` | GPT-4o labels for the 120 bot evaluation sample. |
| `BotCat_LLMLabel_gpt-4o-mini-2024-07-18_120.csv` | GPT-4o-mini labels for the 120 bot evaluation sample. |
| `BotCat_LLMLabel_claude-3-5-sonnet-20241022_120.csv` | Claude 3.5 Sonnet labels for the 120 bot evaluation sample. |
| `BotCat_LLMLabel_gemini-1.5-pro-002_120.csv` | Gemini 1.5 Pro labels for the 120 bot evaluation sample. |
| `BotCat_AllLabels_120.csv` | Combined evaluation file: human labels, all four LLM labels, and majority vote for all 120 bots. |
| `Full_4932_BotFeatures_FunctionOnly.txt` | Human-readable version of the function descriptions for all 4,932 bot tasks. |

### Scripts

**These scripts require API keys to regenerate labels; the final output is already in `data/`.**

| Script | Purpose |
|--------|---------|
| `bot_label_prompt.py` | Shared prompt templates and category descriptions (imported by other scripts). |
| `bot_sample_label_llm.py` | Categorize the 120 bot evaluation sample with a specified LLM (`--model` flag). |
| `bot_label_evaluation.py` | Evaluate LLM accuracy against human expert labels. |
| `bot_full_label_llm.py` | Categorize all 4,932 bot tasks using gpt-4o-2024-11-20, the best performing model. |

### Running the evaluation (no API key required)

```bash
python scripts/bot_label_evaluation.py
```

This reads `data/BotCat_AllLabels_120.csv` and prints accuracy, macro/micro F1, per-category categorization report, and confusion matrix for each model and the majority vote.

### Re-running the LLM categorization (requires API keys)

Set the relevant environment variable(s) before running:

```bash
export OPENAI_API_KEY=sk-...       # for gpt-4o-* models
export ANTHROPIC_API_KEY=sk-ant-... # for claude-* models
export GOOGLE_API_KEY=...           # for gemini-* models
```

Categorize the 120 bot evaluation sample with a specific model:

```bash
python scripts/bot_sample_label_llm.py --model gpt-4o-2024-11-20
python scripts/bot_sample_label_llm.py --model claude-3-5-sonnet-20241022
python scripts/bot_sample_label_llm.py --model gemini-1.5-pro-002
```

Categorize all 4,932 bots (produces the final label file used in the paper):

```bash
python scripts/bot_full_label_llm.py
```

---

## Part 2 — Data Collection Pipeline (Stages 01–05)

> **The final processed dataset is already included in `data/`. Running this pipeline in full is not recommended due to storage and computation time constraints -- a demo mode is available to demonstrate the replicability of the data collection procedure. To reproduce the paper's tables and figures, skip to [Part 3](#part-3--reproducing-results-stages-0611).**

The data collection and processing pipeline demonstrates exactly how the dataset `data/full_sample_project_level_variables.csv` was produced from raw Wikipedia revision histories and other data components.

### Input data files

All input files are already included in `data/`:

| File | Description |
|------|-------------|
| `quarry_project_namespace_all.csv` | Raw output of the Quarry query to fetch all pages in the WikiProject namespace. |
| `quarry_project_category_links.csv` | Raw output of the Quarry query to fetch article–WikiProject membership via `categorylinks`. |
| `all_article_talk_and_project_info_filtered.csv` | Maps each article talk page to its article and its parent WikiProject(s). Assembled from the Quarry SQL outputs above. |
| `Full_4932_LLMLabel_gpt-4o-2024-11-20.csv` | GPT-4o category labels for 4,932 Wikipedia bot tasks across 8 task categories. See [Part 1](#part-1--bot-categorization-pipeline) for how this was produced. |

### How the WikiProject–article mapping was produced (SQL)

The file `all_article_talk_and_project_info_filtered.csv` was assembled from two SQL queries run against [Quarry](https://quarry.wmcloud.org/), a public querying interface for live replicas of Wikipedia databases.

**Query 1:** retrieve all pages in the WikiProject namespace (namespace 4) to identify top-level WikiProjects. The raw output is `data/quarry_project_namespace_all.csv`.

```sql
SELECT page_id, page_title, page_is_redirect
FROM page
WHERE page_namespace = 4;
```

**Query 2:** retrieve article–WikiProject membership via the `categorylinks` table. The raw output is `data/quarry_project_category_links.csv`.

```sql
SELECT cl_to, page_title, page_is_redirect, page_len, page_id
FROM categorylinks
JOIN page ON page_id = cl_from
WHERE page_namespace = 0
  AND cl_to LIKE 'WikiProject_%';
```

### Variable computation methodology

- **Panel structure**: 763 WikiProjects × 288 months (January 2000 – December 2023) = 219,744 rows
- **Bot categorization**: each of the 4,932 bots is assigned to one of 8 task categories (Operational, Interwiki, Information provision, Task allocation, Task division, Exception management, Reward provision, Other) using GPT-4o labels. Four voting rules aggregate labels across tasks: unanimous (`uni`), majority (`maj`), most-frequent (`freq`), and proportional (`prop`).
- **Article quality assessment**: extracted from WikiProject assessment banner templates in article talk page content via regex matching on `class=` fields (FA, GA, A, B, C, Start, Stub).

### Running the collection pipeline

> **Before running:** open `scripts/01_download_revisions.py` and replace the placeholder near the top with your own name and email address:
> ```python
> _CONTACT = 'YOUR_NAME (YOUR_EMAIL)'
> ```
> This is required by [Wikimedia Foundation API usage etiquette](https://www.mediawiki.org/wiki/API:Main_page#Identifying_your_client). Requests without a descriptive User-Agent may be blocked.

#### Demo mode (recommended for verification)

Computes variables for only the **smallest WikiProject** (based on article membership count). Should complete in under 5 minutes on a standard laptop with an internet connection.

```bash
python run_data_processing.py
```

This produces `processed/full_sample_project_level_variables.csv`.

#### Full mode (not recommended without access to and additional setup on a compute cluster)

Computes variables for all 763 WikiProjects and 5,144,817 articles in the final sample.

```bash
python run_data_processing.py --full
```

> **Warning**: This requires a stable internet connection, ~500 GB of free disk space, and several days of compute time on a standard laptop. The original dataset was produced on a high-performance computing cluster using dozens of cores. Full mode runtime on a single machine will be substantially longer.

#### Running individual data collection and processing stages

Each script can also be run independently:

```bash
python scripts/01_download_revisions.py [--full]
python scripts/02_compute_project_variables.py [--full]
python scripts/03_compute_article_page_variables.py [--full]
python scripts/04_compute_article_talk_variables.py [--full]
python scripts/05_assemble_dataset.py [--full] [--date MM_DD_YYYY]
```

---

## Part 3 — Reproducing Results (Stages 06–11)

This section reproduces all tables and figures in the paper based off the processed dataset.

### Option A — Run the full pipeline at once

From the repository root with the virtual environment activated:

```bash
python run_data_analysis.py
```

This runs all six stages in order and prints progress to the terminal. Set `STATA_EXE` first if Stata is not at its default path (see [Prerequisites](#prerequisites)).

---

### Option B — Run each step manually

All commands should be run from the **repository root** with the virtual environment activated.

---

#### Stage 06 — Data Preparation (Stata)

Loads the processed dataset, constructs derived variables (log transformations, quality deltas, standardized revision counts), and saves a Stata panel dataset.

```bash
# macOS / Linux
$STATA_EXE -b do scripts/06_prepare_dataset.do

# Windows
%STATA_EXE% /e do scripts\06_prepare_dataset.do
```

**Input:** `data/full_sample_project_level_variables.csv`

**Output:** `processed/project_month_panel.dta`

---

#### Stage 07 — Regressions and Tables (Stata)

Runs high-dimensional fixed-effects regressions for five quality levels and nine model specifications. Exports regression tables and files containing coefficients and estimates.

```bash
# macOS / Linux
$STATA_EXE -b do scripts/07_run_regressions.do

# Windows
%STATA_EXE% /e do scripts\07_run_regressions.do
```

**Input:** `processed/project_month_panel.dta`

**Output:**
- Regression tables (`.rtf` and `.tex`) in `results/tables/` — see mapping to paper tables below
- `processed/coef_1_all_combined.csv`
- `processed/coef_2_talk_and_art_sep.csv`
- `processed/coef_3_bot_type_art_and_talk_coord.csv`
- `processed/descriptives.csv`

**Table file name → paper table mapping:**

| Output file prefix | Table number in paper |
|--------------------|-------------|
| `1_all_combined` | Table 2 |
| `2_talk_and_art_sep` | Table 3 |
| `3_bot_type_art_and_talk_coord` | Table 4 |
| `rob_1` | Table 5 |
| `rob_2` | Table 6 |
| `rob_3` | Table 7 |
| `rob_4a` | Table 8 |
| `rob_4b` | Table 9 |

---

#### Stage 08 — Margins Computation (Stata)

Estimates predicted margins for the bot x human interaction across a 3 x 3 grid of standardized values, for each of the five quality levels.

```bash
# macOS / Linux
$STATA_EXE -b do scripts/08_combined_marginsplot.do

# Windows
%STATA_EXE% /e do scripts\08_combined_marginsplot.do
```

**Input:** `processed/project_month_panel.dta`

**Output:** `processed/margins_interaction_data.csv`

---

#### Stage 08b — Relative Importance Analysis (Stata)

Estimates the marginal effects of bot edits, human edits, and their interaction for each quality level, then computes each component's share of the total absolute effect.

```bash
# macOS / Linux
$STATA_EXE -b do scripts/08b_relative_importance_analysis.do

# Windows
%STATA_EXE% /e do scripts\08b_relative_importance_analysis.do
```

**Input:** `processed/project_month_panel.dta`

**Output:** `processed/relative_importance.csv`

---

#### Stage 09 — Timeline Figure (Python)

Creates a dual-axis timeline showing total bot edits (above x-axis) and total human edits (below x-axis) over the full observation period.

```bash
python scripts/09_dual_axis_timeline.py
```

**Input:** `processed/project_month_panel.dta`

**Output:** `results/figures/1_timeline.{png,svg}`

---

#### Stage 10 — Main Results Figure (Python)

Creates the two-panel results figure: (A) predicted quality change by bot and human edit levels across quality tiers, and (B) a heatmap of interaction coefficients by human coordination type and bot type.

```bash
python scripts/10_combined_figure.py
```

**Input:**
- `processed/margins_interaction_data.csv`
- `processed/coef_2_talk_and_art_sep.csv`
- `processed/coef_3_bot_type_art_and_talk_coord.csv`
- `processed/descriptives.csv`

**Output:** `results/figures/2_results.{png,svg}`

---

#### Stage 11 — Relative Importance Figure (Python)

Creates a stacked bar chart showing the relative importance of bot edits, human edits, and their interaction across the five quality levels, shown in the appendix.

```bash
python scripts/11_relative_importance_figure.py
```

**Input:** `processed/relative_importance.csv` *(generated by Stage 08b)*

**Output:** `results/figures/3_relative_importance.{png,svg}`
