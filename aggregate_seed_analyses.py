from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent


def read_existing_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tags", nargs="+", required=True)
    parser.add_argument("--out", default="analysis_N10000_slow_3seeds")
    parser.add_argument("--threshold-suffix", default="thr010")
    args = parser.parse_args()

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    family_rows = []
    top_cu_rows = []
    convergence_rows = []

    for tag in args.tags:
        analysis = ROOT / f"analysis_{tag}"

        summary = read_existing_csv(analysis / "structure_summary.csv")
        if summary is not None and not summary.empty:
            row = summary.iloc[0].to_dict()
            row["tag"] = tag
            summary_rows.append(row)

        families = read_existing_csv(analysis / f"voronoi_family_stats_{args.threshold_suffix}.csv")
        if families is not None:
            families["tag"] = tag
            family_rows.append(families)

        top = read_existing_csv(analysis / f"voronoi_top40_by_element_{args.threshold_suffix}.csv")
        if top is not None:
            top = top[top["scope"] == "Cu"].head(12).copy()
            top["tag"] = tag
            top_cu_rows.append(top)

        conv = read_existing_csv(analysis / "convergence_summary.csv")
        if conv is not None:
            conv["tag"] = tag
            convergence_rows.append(conv)

    if not summary_rows:
        raise RuntimeError("No completed seed analyses were found.")

    summaries = pd.DataFrame(summary_rows)
    summaries.to_csv(out / "structure_summary_by_seed.csv", index=False)

    numeric_cols = summaries.select_dtypes(include="number").columns
    summary_stats = summaries[numeric_cols].agg(["mean", "std", "min", "max"]).T.reset_index(names="property")
    summary_stats.to_csv(out / "structure_summary_mean_std.csv", index=False)

    if family_rows:
        families_all = pd.concat(family_rows, ignore_index=True)
        families_all.to_csv(out / "voronoi_family_stats_by_seed.csv", index=False)
        families_stats = (
            families_all.groupby(["scope", "family"])["fraction"]
            .agg(["mean", "std", "min", "max", "count"])
            .reset_index()
        )
        families_stats.to_csv(out / "voronoi_family_stats_mean_std.csv", index=False)

        plot = families_all[
            (families_all["scope"] == "Cu")
            & (families_all["family"].isin(["full_icosahedron_00120", "cn12_ico_like_n5_ge8", "fivefold_rich_n5_ge10"]))
        ].copy()
        labels = {
            "full_icosahedron_00120": "Full ico <0,0,12,0>",
            "cn12_ico_like_n5_ge8": "CN12 ico-like n5>=8",
            "fivefold_rich_n5_ge10": "Fivefold-rich n5>=10",
        }
        plot["label"] = plot["family"].map(labels)
        fig, ax = plt.subplots(figsize=(10, 5.8), constrained_layout=True)
        pivot = plot.pivot(index="tag", columns="label", values="fraction")
        pivot.plot(kind="bar", ax=ax, width=0.78)
        ax.set_xlabel("Seed")
        ax.set_ylabel("Fraction within Cu-centered atoms")
        ax.set_title("Cu-centered motif families across slow-quench seeds")
        ax.tick_params(axis="x", rotation=15)
        ax.legend(frameon=False)
        fig.savefig(out / "cu_motif_families_by_seed.png", dpi=220)
        plt.close(fig)

    if top_cu_rows:
        top_cu = pd.concat(top_cu_rows, ignore_index=True)
        top_cu.to_csv(out / "cu_top_motifs_by_seed.csv", index=False)

    if convergence_rows:
        convergence = pd.concat(convergence_rows, ignore_index=True)
        convergence.to_csv(out / "convergence_summary_by_seed.csv", index=False)

    lines = ["# N10000 Slow-Quench Three-Seed Summary", ""]
    lines.append(f"Completed seed analyses: {len(summaries)} / {len(args.tags)}")
    lines.append("")
    key_props = [
        "final_density_g_cm3",
        "tail_density_g_cm3",
        "tail_pe_per_atom_eV",
        "all_00120_fraction",
        "cu_00120_fraction",
        "cu_cn12_ico_like_n5_ge8_fraction",
        "cu_fivefold_rich_n5_ge10_fraction",
    ]
    for prop in key_props:
        if prop not in summaries:
            continue
        values = summaries[prop].dropna()
        if values.empty:
            continue
        lines.append(f"- {prop}: mean={values.mean():.6g}, std={values.std(ddof=1):.6g}")
    lines.append("")
    lines.append("Generated files:")
    for path in sorted(out.glob("*")):
        lines.append(f"- {path.name}")
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print((out / "summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
