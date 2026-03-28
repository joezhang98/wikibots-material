"""Dual-axis timeline figure (human vs bot edits).

Creates a single figure with bot edits above the x-axis and human edits below.
No title is applied.

Run:
    python scripts/09_dual_axis_timeline.py [--data PATH_TO_DTA] [--out OUTPUT_PNG]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter

from figure_style import apply_house_style, style_axes, style_legend

ROOT_DIR = Path(__file__).resolve().parent.parent


def load_data(dta_path: Path) -> pd.DataFrame:
    return pd.read_stata(dta_path)


def aggregate_monthly(df: pd.DataFrame, columns_to_sum: list[str]) -> pd.DataFrame:
    if "month_count" not in df.columns:
        raise ValueError("month_count column missing in dataset")
    missing = [c for c in columns_to_sum if c not in df.columns]
    cols_present = [c for c in columns_to_sum if c in df.columns]
    if not cols_present:
        raise ValueError(f"None of the requested columns are present: {columns_to_sum}")
    if missing:
        print(f"[dual_axis_timeline] Warning: missing columns skipped: {missing}")
    df_monthly = df.groupby("month_count")[cols_present].sum().reset_index()
    if "year_month" in df.columns:
        df_month = df[["month_count", "year_month"]].drop_duplicates()
        df_monthly = df_monthly.merge(df_month, on="month_count", how="left")
    return df_monthly


def prepare_time_axis(df_monthly: pd.DataFrame) -> pd.DataFrame:
    plot_df = df_monthly.copy()
    if "year_month" in plot_df.columns:
        plot_df["x"] = pd.to_datetime(plot_df["year_month"], errors="coerce")
        plot_df = plot_df.sort_values("x")
        plot_df.attrs["use_datetime"] = True
    else:
        plot_df["x"] = plot_df["month_count"]
        plot_df.attrs["use_datetime"] = False
    return plot_df


def format_xaxis(ax, xs, use_datetime: bool, ensure_last_tick: bool = True):
    if use_datetime:
        locator = AutoDateLocator()
        ax.xaxis.set_major_locator(locator)

        from matplotlib.ticker import FuncFormatter
        concise_fmt = ConciseDateFormatter(locator)

        def custom_formatter(x, pos):
            ticks = ax.get_xticks()
            if len(ticks) > 0 and abs(x - max(ticks)) < 0.5:
                return mdates.num2date(x).strftime("%Y")
            return concise_fmt(x, pos)

        ax.xaxis.set_major_formatter(FuncFormatter(custom_formatter))
        ax.get_figure().autofmt_xdate(rotation=20)

        if ensure_last_tick and len(xs) > 0:
            xmax = pd.to_datetime(pd.Series(xs).dropna().max())
            if pd.notnull(xmax):
                last_tick = float(mdates.date2num(xmax.to_pydatetime()))
                ticks = list(ax.get_xticks())
                if all(abs(t - last_tick) > 0.5 for t in ticks):
                    ticks.append(last_tick)
                    ticks = sorted(set(ticks))
                    ax.set_xticks(ticks)

            ticks = list(ax.get_xticks())
            if len(ticks) > 1 and ticks[-1] - ticks[-2] < 50:
                ticks = ticks[:-2] + [ticks[-1]]
                ax.set_xticks(ticks)
    else:
        xs = list(xs)
        step = max(1, len(xs) // 10)
        ax.set_xticks(xs[::step])
        ax.tick_params(axis="x", rotation=45)


def dual_axis_timeline(
    plot_df: pd.DataFrame,
    human_col: str,
    bot_col: str,
    out_path: Path,
    use_datetime: bool,
    human_label: str = "Human Coordination Edits",
    bot_label: str = "Bot Edits",
    ylabel: str = "Number of Edits",
    xmin_datetime: str | pd.Timestamp | None = "2002-01-01",
    human_color: str = "#4C72B0",
    bot_color: str = "#DD8452",
):
    """Create a timeline plot with bot edits above x-axis and human edits below (inverted)."""
    fig, ax = plt.subplots(figsize=(12, 5))

    x = plot_df["x"].to_numpy()
    human_values = plot_df[human_col].to_numpy()
    bot_values = plot_df[bot_col].to_numpy()

    ax.fill_between(x, 0, bot_values, alpha=0.7, color=bot_color, label=bot_label)
    ax.plot(x, bot_values, color=bot_color, linewidth=1.5)

    ax.fill_between(x, 0, -human_values, alpha=0.7, color=human_color, label=human_label)
    ax.plot(x, -human_values, color=human_color, linewidth=1.5)

    ax.axhline(y=0, color="black", linewidth=0.8)

    bot_max = bot_values.max() * 1.05
    human_max = human_values.max() * 1.05
    ax.set_ylim(-human_max, bot_max)

    ax.set_ylabel(ylabel)
    ax.set_xlabel("Year" if use_datetime else "Month Count")

    leg = ax.legend(loc="upper left")
    style_legend(leg)
    style_axes(ax, grid=False)

    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, pos: f"{abs(v):,.0f}"))

    format_xaxis(ax, x, use_datetime)

    if use_datetime and len(x) > 0:
        xmin_candidate = None if xmin_datetime is None else pd.to_datetime(xmin_datetime)
        xmax = pd.to_datetime(x.max())
        xmax_2024 = pd.to_datetime("2024-12-31")
        xmax = max(xmax, xmax_2024)
        if xmin_candidate is not None and pd.notnull(xmax):
            left = float(mdates.date2num(xmin_candidate.to_pydatetime()))
            right = float(mdates.date2num(xmax.to_pydatetime()))
            ax.set_xlim(left=left, right=right)

        tick_years = [2004, 2008, 2012, 2016, 2020, 2024]
        ax.set_xticks([
            float(mdates.date2num(pd.to_datetime(f'{y}-01-01').to_pydatetime()))
            for y in tick_years
        ])
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"[dual_axis_timeline] Saved {out_path.name}")
    svg_path = out_path.with_suffix(".svg")
    fig.savefig(svg_path, bbox_inches="tight")
    print(f"[dual_axis_timeline] Saved {svg_path.name}")
    plt.close(fig)


def main():
    apply_house_style()
    parser = argparse.ArgumentParser(description="Generate dual-axis timeline figure.")
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT_DIR / "processed" / "project_month_panel.dta",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT_DIR / "results" / "figures" / "1_timeline.png",
    )
    args = parser.parse_args()

    df = load_data(args.data)
    edits_monthly = aggregate_monthly(df, ["art_bot_revs", "human_revs"])
    edits_df = prepare_time_axis(edits_monthly)
    edits_use_datetime = bool(edits_df.attrs.get("use_datetime", False))

    for c in ["art_bot_revs", "human_revs"]:
        if c in edits_df.columns:
            edits_df[c] = edits_df[c].fillna(0)

    args.out.parent.mkdir(parents=True, exist_ok=True)

    dual_axis_timeline(
        edits_df,
        "human_revs",
        "art_bot_revs",
        args.out,
        edits_use_datetime,
        human_label="Human Coordination Edits",
        bot_label="Bot Edits",
        ylabel="Number of Edits",
        xmin_datetime="2002-01-01",
        human_color="#4C72B0",
        bot_color="#DD8452",
    )


if __name__ == "__main__":
    main()
