"""Combined multi-panel figure drawn in a single Matplotlib figure.

Panels
------
  A – Interaction margins grid, 5 panels   (logic from 04b figure marginsplot.py)
  B – Combined interaction heatmap         (logic from 05 heatmap.py)

All three panels are rendered in one plt.figure() via fig.subfigures(), so
fonts, DPI, and axis elements are consistent without any PNG round-tripping.

Output
------
  results/figures/2_results.png
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib.axes import Axes
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
import numpy as np
import pandas as pd
from scipy import stats

from figure_style import apply_house_style, COLORS, SAVEFIG_DPI, style_axes


ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED = ROOT_DIR / "processed"
FIG_DIR = ROOT_DIR / "results" / "figures"
OUTPUT_STEM = FIG_DIR / "2_results"
# Nature Reviews max width: 180 mm
FIG_WIDTH_IN = 180 / 25.4

QUALITY_ORDER = ["Stub", "Start", "C", "B", "A+"]

# Heatmap constants (kept in sync with 05 heatmap.py)
ROW_ORDER_HEATMAP = ["Local", "Central", "", "Coord", "Ex", "Op"]
BORDER_WIDTH = 0.5    # constant border width for every dot

# Extra horizontal inset applied to Panel B on each side, in figure-normalised
# coordinates relative to Panel C's data-area width.  0.0 = no adjustment.
# Increase this if Panel B appears slightly wider than Panel C's dot range.
# Example: 0.015 ≈ 2–3 mm inward per side at 180 mm figure width.
B_SIDE_PADDING: float = 0.015


# ---------------------------------------------------------------------------
# Panel B – Interaction margins grid (5 quality bins)
# ---------------------------------------------------------------------------

def draw_panel_b(axes: list[Axes]) -> tuple[list, list]:
    """5-panel line plot of predicted quality change by bot and human edits."""
    df = pd.read_csv(PROCESSED / "margins_interaction_data.csv")
    quality_order = ["stub", "start", "c", "b", "a"]
    human_colors = {-1: COLORS.RED, 0: COLORS.GRAY, 1: COLORS.GREEN}
    human_labels = {-1: "\u22121 SD", 0: "Mean", 1: "+1 SD"}

    for idx, (qual, ax) in enumerate(zip(quality_order, axes)):
        qual_data = df[df["quality"] == qual]
        for human_level in [-1, 0, 1]:
            subset = (
                qual_data[qual_data["human_level"] == human_level]
                .sort_values("bot_level")
            )
            color = human_colors[human_level]
            ax.plot(
                subset["bot_level"], subset["margin"],
                marker="o", color=color, linewidth=1.6,
                markersize=5, label=human_labels[human_level],
            )
            ax.fill_between(
                subset["bot_level"], subset["ci_lower"], subset["ci_upper"],
                color=color, alpha=0.15,
            )
        ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
        style_axes(ax)
        ax.set_title(QUALITY_ORDER[idx])
        ax.set_xlabel("Bot Edits" if idx == 2 else "")
        ax.set_xticks([-1, 0, 1])
        ax.set_xticklabels(["-1", "0", "+1"])
        ax.set_ylim(0, 3)
        ax.set_yticks([0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
        if idx == 0:
            ax.set_ylabel("Predicted Quality Change")
        else:
            ax.tick_params(axis="y", labelleft=False)

    handles, labels = axes[0].get_legend_handles_labels()
    return handles, labels


# ---------------------------------------------------------------------------
# Panel C – Combined interaction heatmap
# ---------------------------------------------------------------------------

def _load_descriptives(path: Path) -> dict[str, float]:
    """Read mean values from descriptives.csv for dot sizing."""
    if not path.exists():
        return {}
    key_to_label = {
        "art_talk_human_revs_log": "Local",
        "wp_human_revs_log": "Central",
        "aa_bot_coord_maj_revs_log": "Coord",
        "aa_bot_ex_maj_revs_log": "Ex",
        "aa_bot_op_maj_revs_log": "Op",
    }
    try:
        with open(path, "r") as fh:
            lines = fh.readlines()
        size_map: dict[str, float] = {}
        for line in lines[3:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 2:
                continue

            def _clean(s: str) -> str:
                s = s.strip()
                if s.startswith('="') and s.endswith('"'):
                    return s[2:-1]
                return s[1:] if s.startswith("=") else s

            row_label = _clean(parts[0])
            mean_str = _clean(parts[1])
            try:
                mean_val = float(mean_str)
            except ValueError:
                continue
            if row_label in key_to_label:
                size_map[key_to_label[row_label]] = mean_val
        return size_map
    except Exception:
        return {}


def _scale_sizes(
    values: pd.Series, min_size: float = 200, max_size: float = 600
) -> pd.Series:
    mn, mx = values.min(), values.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series((min_size + max_size) / 2.0, index=values.index)
    return min_size + (values - mn) / (mx - mn) * (max_size - min_size)


def _normalize_qual(val: object) -> str:
    qual_map = {"stub": "Stub", "start": "Start", "c": "C", "b": "B", "a": "A+"}
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    text = str(val).strip()
    if text in QUALITY_ORDER:
        return text
    lowered = text.lower()
    if lowered in qual_map:
        return qual_map[lowered]
    if text.upper() == "A":
        return "A+"
    if text.upper() in {"B", "C"}:
        return text.upper()
    return text


def _build_heatmap_df() -> tuple[pd.DataFrame, TwoSlopeNorm, LinearSegmentedColormap]:
    """Load and prepare heatmap data (mirrors logic in 05 heatmap.py)."""
    df10 = pd.read_csv(PROCESSED / "coef_2_talk_and_art_sep.csv")
    df9 = pd.read_csv(PROCESSED / "coef_3_bot_type_art_and_talk_coord.csv")

    talk_rows: list[dict] = []
    wp_rows: list[dict] = []
    for i in range(len(QUALITY_ORDER)):
        row = df10[df10["number"] == i + 1].iloc[0]
        talk_rows.append({
            "row_label": "Local", "qual": QUALITY_ORDER[i],
            "b": row["b_art"], "se": row["se_art"],
            "ub": row["ub_art"], "lb": row["lb_art"],
        })
        wp_rows.append({
            "row_label": "Central", "qual": QUALITY_ORDER[i],
            "b": row["b_wp"], "se": row["se_wp"],
            "ub": row["ub_wp"], "lb": row["lb_wp"],
        })

    bot_map = {"coord": "Coord", "ex": "Ex", "op": "Op"}
    df9_f = df9[df9["bot"].isin(bot_map)].copy()
    df9_f["row_label"] = df9_f["bot"].map(bot_map)
    bot_rows = df9_f[["row_label", "qual", "b", "se", "ub", "lb"]].to_dict("records")

    df = pd.DataFrame(talk_rows + wp_rows + bot_rows)
    df["qual"] = df["qual"].apply(_normalize_qual)
    df["z"] = df["b"] / df["se"]
    df["p"] = 2 * (1 - stats.norm.cdf(abs(df["z"])))

    size_lookup = _load_descriptives(PROCESSED / "descriptives.csv")
    df["raw_size"] = df["row_label"].map(size_lookup).fillna(1.0)
    df["size"] = _scale_sizes(df["raw_size"])

    qual_to_x = {q: i for i, q in enumerate(QUALITY_ORDER)}
    row_to_y = {r: i for i, r in enumerate(ROW_ORDER_HEATMAP)}
    df["x"] = df["qual"].map(qual_to_x)
    df["y"] = df["row_label"].map(row_to_y)

    vmax = max(df["b"].abs().max(), 0.05)
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    cmap = LinearSegmentedColormap.from_list(
        "RedWhiteGreen", [COLORS.RED, "#FFFFFF", COLORS.GREEN], N=256
    )
    return df, norm, cmap


def draw_panel_c(
    ax: Axes,
    cax: Axes,
    qual_x_positions: list[float] | None = None,
) -> tuple[list[object], pd.DataFrame]:
    """Dot-style heatmap of interaction coefficients with colorbar.

    qual_x_positions: if provided, scatter dots and x-ticks are placed at
    these data-coordinate x-positions (one per QUALITY_ORDER entry) instead
    of the default integers 0..4.  Pass the values returned by
    _compute_alignment_positions() to align with Panel B subplot centres.
    """
    df, norm, cmap = _build_heatmap_df()

    if qual_x_positions is not None:
        qual_to_x = dict(zip(QUALITY_ORDER, qual_x_positions))
        df["x"] = df["qual"].map(qual_to_x)
        x_ticks = list(qual_x_positions)
        spacing = (qual_x_positions[-1] - qual_x_positions[0]) / (len(QUALITY_ORDER) - 1)
        x_lim = (qual_x_positions[0] - spacing / 2, qual_x_positions[-1] + spacing / 2)
    else:
        x_ticks = list(range(len(QUALITY_ORDER)))
        x_lim = (-0.5, len(QUALITY_ORDER) - 0.5)

    df_sig = df[df["p"] <= 0.05]
    df_insig = df[df["p"] > 0.05]

    scatter_sig = ax.scatter(
        df_sig["x"], df_sig["y"],
        c=df_sig["b"], cmap=cmap, norm=norm,
        s=df_sig["size"],
        edgecolor="black", linewidths=BORDER_WIDTH,
        linestyle="-",
    )
    scatter_insig = ax.scatter(
        df_insig["x"], df_insig["y"],
        c=df_insig["b"], cmap=cmap, norm=norm,
        s=df_insig["size"],
        edgecolor="black", linewidths=BORDER_WIDTH,
        linestyle=(0, (4, 5)),
    )
    style_axes(ax, grid=False)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(QUALITY_ORDER)
    ax.set_xlabel("Quality")
    ax.set_xlim(*x_lim)
    ax.set_yticks(range(len(ROW_ORDER_HEATMAP)))
    ax.set_yticklabels([r if r else "" for r in ROW_ORDER_HEATMAP])
    ax.set_ylabel("Interaction Type")
    ax.set_ylim(-0.5, len(ROW_ORDER_HEATMAP) + 0.1)
    ax.invert_yaxis()

    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, cax=cax)
    cbar.set_label("Interaction Coefficient")
    return [scatter_sig, scatter_insig], df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _refine_panel_c(
    ax: Axes,
    scatters: list[object],
    df: pd.DataFrame,
    qual_x_positions: list[float],
) -> None:
    """Move scatter dots, x-ticks, and xlim to refined positions.

    Called after a second fig.canvas.draw() so the positions reflect the
    fully-settled layout (Panel C's x-tick labels and colorbar are already
    in place).  Updating these three things together keeps dots and labels
    at identical coordinates.
    """
    qual_to_x = dict(zip(QUALITY_ORDER, qual_x_positions))
    scatter_sig, scatter_insig = scatters  # type: ignore[misc]
    for sc, sub in [(scatter_sig, df[df["p"] <= 0.05]), (scatter_insig, df[df["p"] > 0.05])]:
        if len(sub):
            new_x = sub["qual"].map(qual_to_x).values
            sc.set_offsets(np.column_stack([new_x, sub["y"].values]))  # type: ignore[attr-defined]
    spacing = (qual_x_positions[-1] - qual_x_positions[0]) / (len(QUALITY_ORDER) - 1)
    x_lim = (qual_x_positions[0] - spacing / 2, qual_x_positions[-1] + spacing / 2)
    ax.set_xticks(qual_x_positions)
    ax.set_xticklabels(QUALITY_ORDER)
    ax.set_xlim(*x_lim)


def _compute_alignment_positions(ref_axes: list[Axes], target_ax: Axes) -> list[float]:
    """Return x-positions in target_ax's current data coordinates that
    correspond to the pixel-centres of ref_axes.  Uses normalised figure
    coordinates (ax.get_position()), so no renderer is needed.  Must be
    called after fig.canvas.draw() has resolved all layout positions.
    """
    pos_t = target_ax.get_position()
    xlim = target_ax.get_xlim()

    positions = []
    for ax in ref_axes:
        pos = ax.get_position()
        center_fig = (pos.x0 + pos.x1) / 2
        frac = (center_fig - pos_t.x0) / (pos_t.x1 - pos_t.x0)
        positions.append(xlim[0] + frac * (xlim[1] - xlim[0]))
    return positions


def _apply_panel_b_side_padding(
    axes_b: list[Axes],
    ref_ax: Axes,
    pad: float,
) -> None:
    """Shift each Panel B axis inward by *pad* (figure-normalised units) on
    both sides, preserving relative subplot widths.

    Must be called after ``fig.set_layout_engine("none")`` so that
    ``ax.set_position()`` is not overridden by constrained_layout.
    *pad* is expressed as a fraction of *ref_ax*'s horizontal extent;
    adjust ``B_SIDE_PADDING`` at the top of the file to taste.
    """
    pos_c = ref_ax.get_position()
    total_w = pos_c.x1 - pos_c.x0
    if total_w <= 0 or pad <= 0:
        return
    new_left = pos_c.x0 + pad
    new_right = pos_c.x1 - pad
    scale = (new_right - new_left) / total_w
    for ax in axes_b:
        pos = ax.get_position()
        rel_x0 = pos.x0 - pos_c.x0
        rel_x1 = pos.x1 - pos_c.x0
        ax.set_position((
            new_left + rel_x0 * scale,
            pos.y0,
            (rel_x1 - rel_x0) * scale,
            pos.height,
        ))


# ---------------------------------------------------------------------------
# Main – assemble all panels in one figure
# ---------------------------------------------------------------------------

def main() -> None:
    apply_house_style()

    fig = plt.figure(figsize=(FIG_WIDTH_IN, 5.5), layout="constrained")

    # Single GridSpec: 2 rows × 6 cols (5 data cols + 1 narrow colorbar col).
    # Under constrained_layout, axes sharing the same column get the same left
    # and right boundaries — so ax_b[0] and ax_c align automatically, driven
    # by whichever has the wider y-axis text (Panel C's row labels).
    gs = fig.add_gridspec(
        2, 6,
        height_ratios=[2.8, 3.5],
        width_ratios=[1, 1, 1, 1, 1, 0.1],
        hspace=0.1,
        wspace=0.08,
    )

    # --- Panel C axes: created first so y-axis labels are visible to
    #     constrained_layout when it computes Panel B's left boundary. ---
    ax_c = fig.add_subplot(gs[1, :5])
    ax_cbar = fig.add_subplot(gs[1, 5])
    ax_c.set_yticks(range(len(ROW_ORDER_HEATMAP)))
    ax_c.set_yticklabels([r if r else "" for r in ROW_ORDER_HEATMAP])
    ax_c.set_ylabel("Interaction Type")
    ax_c.set_ylim(-0.5, len(ROW_ORDER_HEATMAP) + 0.1)  # match draw_panel_c
    style_axes(ax_c, grid=False)

    # --- Panel B: one axis per column in row 0 ---
    ax_b0 = fig.add_subplot(gs[0, 0])
    axes_b = [ax_b0] + [fig.add_subplot(gs[0, i], sharey=ax_b0) for i in range(1, 5)]
    legend_handles, legend_labels = draw_panel_b(axes_b)

    # Pass 1: layout with Panel B drawn and Panel C y-axis in place.
    # Gives approximate Panel B subplot centres in Panel C's coords.
    fig.canvas.draw()
    qual_x_positions = _compute_alignment_positions(axes_b, ax_c)
    scatters, df_c = draw_panel_c(ax_c, ax_cbar, qual_x_positions=qual_x_positions)

    # Pass 2: re-settle layout now that Panel C has its scatter data, x-tick
    # labels, and colorbar, then recompute positions and update dots + ticks.
    fig.canvas.draw()
    qual_x_positions = _compute_alignment_positions(axes_b, ax_c)
    _refine_panel_c(ax_c, scatters, df_c, qual_x_positions)

    # Pass 3: one more round after the xlim/offsets changed in Pass 2, so the
    # positions we read are the fully-settled ones.
    fig.canvas.draw()
    qual_x_positions = _compute_alignment_positions(axes_b, ax_c)
    _refine_panel_c(ax_c, scatters, df_c, qual_x_positions)

    # Freeze the layout engine so that fig.savefig() does NOT re-run
    # constrained_layout and undo the alignment we just computed.
    fig.set_layout_engine("none")

    # Nudge Panel B inward by B_SIDE_PADDING on each side, then re-sync
    # Panel C's dots to the new subplot centres.
    if B_SIDE_PADDING > 0:
        _apply_panel_b_side_padding(axes_b, ax_c, B_SIDE_PADDING)
        qual_x_positions = _compute_alignment_positions(axes_b, ax_c)
        _refine_panel_c(ax_c, scatters, df_c, qual_x_positions)

    # Place legend to the right of the last Panel B axis using frozen figure
    # coordinates, so constrained_layout is not affected.
    pos_last = axes_b[-1].get_position()
    fig.legend(
        legend_handles, legend_labels,
        title="Human\nCoordination",
        loc="center left",
        bbox_to_anchor=(pos_last.x1 + 0.01, (pos_last.y0 + pos_last.y1) / 2),
        bbox_transform=fig.transFigure,
        frameon=False,
        fontsize=9,
        title_fontsize=9,
    )

    OUTPUT_STEM.parent.mkdir(parents=True, exist_ok=True)
    for suffix, kwargs in [(".png", {"dpi": SAVEFIG_DPI}), (".svg", {})]:
        out = OUTPUT_STEM.with_suffix(suffix)
        fig.savefig(out, **kwargs)
        print(f"Saved: {out}")
    plt.close(fig)


if __name__ == "__main__":
    main()
