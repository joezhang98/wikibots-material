"""Analysis pipeline — Human Coordination Shapes the Promise and
Limits of Autonomous Agents.

Runs the full analysis: prepares the dataset, runs regressions, and
produces all tables and figures reported in the paper.

Run from the repository root (or from anywhere — the script locates itself
automatically):

    python run_data_analysis.py

Requirements
------------
Stata 16 or higher
    The script auto-detects Stata by scanning common install locations across
    versions (16–25) and editions (MP, SE, BE/IC), newest versions first.
    If your Stata is not found automatically, set the STATA_EXE environment
    variable to the full path of your Stata executable:

        export STATA_EXE=/path/to/stata-mp          # macOS / Linux
        set STATA_EXE=C:\path\to\StataSE-64.exe     # Windows

Python 3.10+
    Packages listed in requirements.txt.

Input
-----
    data/full_sample_project_level_variables.csv

Pipeline
--------
  1. Create output directories
  2. Stata: scripts/06_prepare_dataset.do              → processed/project_month_panel.dta
  3. Stata: scripts/07_run_regressions.do              → processed/coef_*.csv + results/tables/
  4. Stata: scripts/08_combined_marginsplot.do         → processed/margins_interaction_data.csv
  5. Stata: scripts/08b_relative_importance_analysis.do → processed/relative_importance.csv
  6. Python: scripts/09_dual_axis_timeline.py
  7. Python: scripts/10_combined_figure.py
  8. Python: scripts/11_relative_importance_figure.py
"""

from __future__ import annotations

import glob
import os
import platform
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT_DIR / "scripts"

# ---------------------------------------------------------------------------
# Stata executable — auto-detect by OS, override via STATA_EXE env var
# ---------------------------------------------------------------------------

_SYSTEM = platform.system()


def _find_stata() -> str:
    """Return the path of the first Stata 16+ executable found on this machine.

    Searches common install locations across versions (16–25) and editions
    (MP > SE > BE/IC), newest versions first.  Returns an empty string if
    nothing is found so the caller can emit a clear error message.
    """
    if _SYSTEM == "Windows":
        _STATA_BATCH_FLAGS[:] = ["/e", "do"]
        editions = ["StataMP", "StataSE", "StataBE", "StataIC"]
        for v in range(25, 15, -1):
            for ed in editions:
                for root in [r"C:\Program Files", r"C:\Program Files (x86)"]:
                    for name in [f"{ed}-64.exe", f"{ed}.exe"]:
                        p = os.path.join(root, f"Stata{v}", name)
                        if os.path.isfile(p):
                            return p
        return ""
    elif _SYSTEM == "Darwin":  # macOS
        _STATA_BATCH_FLAGS[:] = ["-b", "do"]
        # App bundle patterns: /Applications/Stata19/StataMP.app/… or
        # /Applications/StataNow/StataMP.app/… or /Applications/StataMP.app/…
        exe_names = ["stata-mp", "stata-se", "stata-be", "stata"]
        app_names = ["StataMP", "StataSE", "StataBE", "StataIC", "Stata"]
        dir_patterns = [
            "/Applications/Stata[0-9]*/",
            "/Applications/StataNow/",
            "/Applications/Stata/",
            "/Applications/",
        ]
        for dp in dir_patterns:
            for app in app_names:
                for exe in exe_names:
                    pattern = f"{dp}{app}.app/Contents/MacOS/{exe}"
                    hits = sorted(glob.glob(pattern), reverse=True)
                    if hits:
                        return hits[0]
        return ""
    else:  # Linux
        _STATA_BATCH_FLAGS[:] = ["-b", "do"]
        exe_names = ["stata-mp", "stata-se", "stata-be", "stata"]
        for v in range(25, 15, -1):
            for exe in exe_names:
                p = f"/usr/local/stata{v}/{exe}"
                if os.path.isfile(p):
                    return p
        # Also try unversioned path
        for exe in exe_names:
            p = f"/usr/local/stata/{exe}"
            if os.path.isfile(p):
                return p
        return ""


_STATA_BATCH_FLAGS: list[str] = []
_DEFAULT_STATA = _find_stata()
STATA_EXE = os.environ.get("STATA_EXE", _DEFAULT_STATA)

# ---------------------------------------------------------------------------
# Script lists
# ---------------------------------------------------------------------------

DO_FILES = [
    SCRIPTS_DIR / "06_prepare_dataset.do",
    SCRIPTS_DIR / "07_run_regressions.do",
    SCRIPTS_DIR / "08_combined_marginsplot.do",
    SCRIPTS_DIR / "08b_relative_importance_analysis.do",
]

PY_SCRIPTS = [
    SCRIPTS_DIR / "09_dual_axis_timeline.py",
    SCRIPTS_DIR / "10_combined_figure.py",
    SCRIPTS_DIR / "11_relative_importance_figure.py",
]

OUTPUT_DIRS = [
    ROOT_DIR / "processed",
    ROOT_DIR / "results" / "figures",
    ROOT_DIR / "results" / "tables",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def banner(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def run_stata(do_file: Path) -> None:
    """Run a Stata do-file in batch mode (no GUI)."""
    banner(f"Stata: {do_file.name}")
    if not STATA_EXE or not Path(STATA_EXE).exists():
        print("ERROR: Stata executable not found.")
        print("Stata 16 or higher is required. If it is installed, set the STATA_EXE")
        print("environment variable to the full path of your Stata executable, e.g.:")
        print("  export STATA_EXE=/path/to/stata-mp          # macOS/Linux")
        print("  set STATA_EXE=C:\\path\\to\\StataSE-64.exe  # Windows")
        sys.exit(1)
    cmd = [STATA_EXE] + _STATA_BATCH_FLAGS + [str(do_file)]
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    if result.returncode != 0:
        print(f"ERROR: Stata exited with code {result.returncode} for {do_file.name}")
        log = ROOT_DIR / (do_file.stem + ".log")
        if log.exists():
            print(f"See log: {log}")
        sys.exit(result.returncode)
    print(f"OK: {do_file.name}")


def run_python(script: Path) -> None:
    """Run a Python script using the current interpreter."""
    banner(f"Python: {script.name}")
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT_DIR)
    if result.returncode != 0:
        print(f"ERROR: Python exited with code {result.returncode} for {script.name}")
        sys.exit(result.returncode)
    print(f"OK: {script.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"Repository root : {ROOT_DIR}")
    print(f"Platform        : {_SYSTEM}")
    if STATA_EXE:
        print(f"Stata executable: {STATA_EXE} (auto-detected)" if not os.environ.get("STATA_EXE") else f"Stata executable: {STATA_EXE} (from STATA_EXE)")
    else:
        print("Stata executable: not found (set STATA_EXE if Stata is installed)")

    # Step 1: Create output directories
    banner("Step 1: Creating output directories")
    for d in OUTPUT_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  {d.relative_to(ROOT_DIR)}/")

    # Steps 2–5: Stata pipeline
    for i, do_file in enumerate(DO_FILES, start=2):
        banner(f"Step {i}: {do_file.name}")
        run_stata(do_file)

    # Steps 6–8: Python figures
    for i, script in enumerate(PY_SCRIPTS, start=6):
        banner(f"Step {i}: {script.name}")
        run_python(script)

    banner("All steps complete")
    print(f"\nOutputs written to:")
    print(f"  {ROOT_DIR / 'results' / 'figures'}/")
    print(f"  {ROOT_DIR / 'results' / 'tables'}/")
    print(f"  {ROOT_DIR / 'processed'}/")


if __name__ == "__main__":
    main()
