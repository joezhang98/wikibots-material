"""Shared Matplotlib "house style" for Wiki Bots analysis figures.

Goal: make all Python-generated figures look consistent (fonts, colors, grid,
spines, DPI, legend styling).

Usage:
    from figure_style import apply_house_style, style_axes, COLORS, SAVEFIG_DPI
    apply_house_style()

This module is intentionally lightweight and only depends on Matplotlib.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import matplotlib as mpl
from cycler import cycler
from matplotlib.legend import Legend


SAVEFIG_DPI: int = 400


@dataclass(frozen=True)
class _Colors:
    BLUE: str = "#4C72B0"   # used for "human" in timeline_graphs
    ORANGE: str = "#DD8452" # used for "bot" in timeline_graphs
    GRAY: str = "#999999"

    GREEN: str = "#55A868"
    RED: str = "#C44E52"
    PURPLE: str = "#8172B3"
    BROWN: str = "#937860"
    PINK: str = "#DA8BC3"


COLORS = _Colors()


def apply_house_style(*, savefig_dpi: int = SAVEFIG_DPI) -> None:
    """Apply consistent Matplotlib rcParams for all figures."""

    # Use a color cycle with our preferred lead colors.
    prop_cycle = cycler(
        color=[
            COLORS.BLUE,
            COLORS.ORANGE,
            COLORS.GREEN,
            COLORS.RED,
            COLORS.PURPLE,
            COLORS.BROWN,
            COLORS.PINK,
            COLORS.GRAY,
        ]
    )

    mpl.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
            "savefig.dpi": savefig_dpi,

            # Fonts
            # Prefer journal-common sans fonts; fall back safely.
            # (Matplotlib will use the first available font on the system.)
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "Nimbus Sans", "DejaVu Sans"],
            "font.size": 8,
            "axes.titlesize": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,

            # Axes
            # Top journals typically prefer no gridlines (unless needed).
            "axes.grid": False,
            "axes.edgecolor": "black",
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,

            # Ticks
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.size": 3.5,
            "ytick.major.size": 3.5,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,

            # Lines/markers
            "lines.linewidth": 1.6,
            "lines.markersize": 6,
            "errorbar.capsize": 4,

            # Legend
            "legend.frameon": False,
            "legend.fontsize": 8,
            "legend.title_fontsize": 8,

            "axes.prop_cycle": prop_cycle,
        }
    )


def style_axes(ax, *, grid: bool | None = None) -> None:
    """Apply per-axis styling (spines + grid toggle)."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid is not None:
        ax.grid(grid)


def style_legend(legend: Legend | None, *, edgecolor: str = "black", linewidth: float = 0.6) -> None:
    """Add a subtle outline to legend handles for better readability.

    Works for common legend artists (Patch/PolyCollection/Line2D).
    """
    if legend is None:
        return

    for handle in getattr(legend, "legend_handles", []):
        # Filled patches/collections
        if hasattr(handle, "set_edgecolor"):
            try:
                handle.set_edgecolor(edgecolor)
            except Exception:
                pass
        if hasattr(handle, "set_linewidth"):
            try:
                handle.set_linewidth(linewidth)
            except Exception:
                pass

        # Lines with markers
        if hasattr(handle, "set_markeredgecolor"):
            try:
                handle.set_markeredgecolor(edgecolor)
            except Exception:
                pass
        if hasattr(handle, "set_markeredgewidth"):
            try:
                handle.set_markeredgewidth(linewidth)
            except Exception:
                pass


def palette_dict() -> Dict[str, str]:
    """Convenience mapping for scripts that prefer dict lookups."""
    return {
        "blue": COLORS.BLUE,
        "orange": COLORS.ORANGE,
        "gray": COLORS.GRAY,
        "green": COLORS.GREEN,
        "red": COLORS.RED,
        "purple": COLORS.PURPLE,
        "brown": COLORS.BROWN,
        "pink": COLORS.PINK,
    }
