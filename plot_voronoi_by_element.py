from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

OUT = Path("analysis")
df = pd.read_csv(OUT / "voronoi_by_element.csv")

fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
for ax, elem in zip(axes, ["Cu", "Zr"]):
    sub = df[df.element == elem].head(12).iloc[::-1]
    colors = ["#b85c38" if idx == "<0,0,12,0>" else "#4f7f9f" for idx in sub.voronoi_index]
    ax.barh(sub.voronoi_index, sub.fraction_within_element, color=colors)
    ax.set_title(f"{elem}-centered Voronoi motifs")
    ax.set_xlabel("Fraction within element")
    ax.set_xlim(0, max(0.11, sub.fraction_within_element.max() * 1.15))

fig.savefig(OUT / "voronoi_by_element_top12.png", dpi=220)

print("Wrote analysis/voronoi_by_element_top12.png")
