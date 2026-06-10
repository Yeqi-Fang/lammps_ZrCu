import pandas as pd

df = pd.read_csv("analysis/voronoi_per_atom.csv")

# 假设 type 1 = Cu, type 2 = Zr
df["element"] = df["type"].map({1: "Cu", 2: "Zr"})

df["vindex"] = (
    "<"
    + df["n3"].astype(int).astype(str) + ","
    + df["n4"].astype(int).astype(str) + ","
    + df["n5"].astype(int).astype(str) + ","
    + df["n6"].astype(int).astype(str)
    + ">"
)

for elem in ["Cu", "Zr"]:
    sub = df[df["element"] == elem]
    print("\n", elem, "centered motifs")
    print(sub["vindex"].value_counts(normalize=True).head(15) * 100)

print("\nFull icosahedron by element:")
for elem in ["Cu", "Zr"]:
    sub = df[df["element"] == elem]
    frac = (sub["vindex"] == "<0,0,12,0>").mean() * 100
    print(elem, frac)