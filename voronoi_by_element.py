from __future__ import annotations

import pandas as pd

atoms = pd.read_csv("analysis/voronoi_per_atom.csv")
atoms["vindex"] = atoms.apply(
    lambda r: f"<{int(r.n3)},{int(r.n4)},{int(r.n5)},{int(r.n6)}>",
    axis=1,
)

rows = []
for elem in ["Cu", "Zr"]:
    sub = atoms[atoms.element == elem]
    counts = sub.vindex.value_counts()
    print(f"\n{elem} N={len(sub)}")
    table = counts.head(15).to_frame("count")
    table["fraction"] = table["count"] / len(sub)
    print(table.to_string())
    for idx, count in counts.items():
        rows.append(
            {
                "element": elem,
                "voronoi_index": idx,
                "count": int(count),
                "fraction_within_element": float(count / len(sub)),
            }
        )

pd.DataFrame(rows).to_csv("analysis/voronoi_by_element.csv", index=False)
