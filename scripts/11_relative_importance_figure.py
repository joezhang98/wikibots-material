"""Relative importance analysis figure: stacked bar chart showing bot/human/interaction contributions."""
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from figure_style import apply_house_style, SAVEFIG_DPI, style_axes, COLORS

ROOT_DIR = Path(__file__).resolve().parent.parent

# Load the data
df = pd.read_csv(ROOT_DIR / 'processed' / 'relative_importance.csv')

# Print data for inspection
print("Data loaded:")
print(df)
print("\nPercentages sum:", df[['pct_bot', 'pct_human', 'pct_interaction']].sum(axis=1))

# Prepare data for plotting (convert to numpy arrays explicitly)
quality_levels = df['qual_label'].to_numpy()
bot_pct = df['pct_bot'].to_numpy()
human_pct = df['pct_human'].to_numpy()
interaction_pct = df['pct_interaction'].to_numpy()

# Apply house style
apply_house_style()

# Set up the plot
fig, ax = plt.subplots(figsize=(8, 4))

# Create positions for bars
x = np.arange(len(quality_levels))
width = 0.6

# Create stacked bars using house style colors (bottom to top: interaction, bot, human)
p1 = ax.bar(x, interaction_pct, width, label='Interaction', color=COLORS.PURPLE)
p2 = ax.bar(x, bot_pct, width, bottom=interaction_pct, label='Bot Edits', color=COLORS.ORANGE)
p3 = ax.bar(x, human_pct, width, bottom=interaction_pct + bot_pct,
            label='Human Coord. Edits', color=COLORS.BLUE)

# Customize the plot
ax.set_ylabel('Relative Importance (%)')
ax.set_xlabel('Quality Level')
ax.set_title('')
ax.set_xticks(x)
ax.set_xticklabels(quality_levels)
ax.legend(handles=[p3, p2, p1], loc='best', frameon=True, facecolor='white', edgecolor='black')

# Apply axes styling
style_axes(ax, grid=False)

# Add percentage labels on bars
for i, (b, h, inter) in enumerate(zip(bot_pct, human_pct, interaction_pct)):
    # Interaction label (bottom)
    if inter > 5:
        ax.text(i, inter/2, f'{inter:.1f}%', ha='center', va='center',
                fontweight='bold', fontsize=9, color='white')

    # Bot label (middle)
    if b > 5:  # Only show if segment is large enough
        ax.text(i, inter + b/2, f'{b:.1f}%', ha='center', va='center',
                fontweight='bold', fontsize=9, color='white')

    # Human label (top)
    if h > 5:
        ax.text(i, inter + b + h/2, f'{h:.1f}%', ha='center', va='center',
                fontweight='bold', fontsize=9, color='white')

# Set y-axis limit
ax.set_ylim(0, 100)

# Tight layout
plt.tight_layout()

# Save the figure
output_path = ROOT_DIR / 'results' / 'figures' / '3_relative_importance.png'
fig.savefig(output_path, dpi=SAVEFIG_DPI)
print(f"\nFigure saved to: {output_path}")
svg_path = output_path.with_suffix('.svg')
fig.savefig(svg_path)
print(f"Figure saved to: {svg_path}")

plt.close(fig)

# Create a summary table
print("\n" + "="*60)
print("SUMMARY: Relative Importance by Quality Level")
print("="*60)
for i, row in df.iterrows():
    print(f"\n{row['qual_label']} Quality:")
    print(f"  Bot edits:        {row['pct_bot']:6.2f}% (effect: {row['bot_effect']:7.4f})")
    print(f"  Human edits:      {row['pct_human']:6.2f}% (effect: {row['human_effect']:7.4f})")
    print(f"  Interaction:      {row['pct_interaction']:6.2f}% (effect: {row['interaction_effect']:7.4f})")
    print(f"  Total:            {row['pct_bot'] + row['pct_human'] + row['pct_interaction']:6.2f}%")
print("="*60)
