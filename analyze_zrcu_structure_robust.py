from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from ovito.io import export_file, import_file
from ovito.modifiers import CoordinationAnalysisModifier, PythonScriptModifier, VoronoiAnalysisModifier


ROOT = Path(__file__).resolve().parent
TYPE_NAMES = {1: "Cu", 2: "Zr"}
TYPE_RADII = {1: 1.35, 2: 1.55}
PRIMARY_THRESHOLD = 0.10
THRESHOLDS = (0.05, 0.10, 0.20)


def configure_types(frame, data):
    types = data.particles_.particle_types_
    for type_id, name in TYPE_NAMES.items():
        particle_type = types.type_by_id_(type_id)
        particle_type.name = name
        particle_type.radius = TYPE_RADII.get(type_id, 1.45)


def load_thermo(path: Path) -> pd.DataFrame:
    names = [
        "step",
        "time_ps",
        "temp_K",
        "press_bar",
        "pxx_bar",
        "pyy_bar",
        "pzz_bar",
        "pxy_bar",
        "pe_eV",
        "ke_eV",
        "etotal_eV",
        "pe_per_atom_eV",
        "ke_per_atom_eV",
        "vol_A3",
        "vol_per_atom_A3",
        "density_g_cm3",
    ]
    return pd.read_csv(path, comment="#", sep=r"\s+", names=names)


def save_thermo_plots(thermo: pd.DataFrame, out: Path) -> dict[str, float]:
    thermo.to_csv(out / "thermo_history.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    axes[0, 0].plot(thermo["time_ps"], thermo["temp_K"], lw=1.3)
    axes[0, 0].set_xlabel("Time (ps)")
    axes[0, 0].set_ylabel("Temperature (K)")
    axes[0, 0].set_title("Temperature")

    axes[0, 1].plot(thermo["time_ps"], thermo["density_g_cm3"], lw=1.3, color="#2f6f5e")
    axes[0, 1].set_xlabel("Time (ps)")
    axes[0, 1].set_ylabel("Density (g/cm3)")
    axes[0, 1].set_title("Density")

    axes[1, 0].plot(thermo["time_ps"], thermo["pe_per_atom_eV"], lw=1.3, color="#7b4f9f")
    axes[1, 0].set_xlabel("Time (ps)")
    axes[1, 0].set_ylabel("PE/atom (eV)")
    axes[1, 0].set_title("Potential Energy")

    axes[1, 1].plot(thermo["time_ps"], thermo["press_bar"] * 1.0e-4, lw=1.1, color="#9a4e3a")
    axes[1, 1].axhline(0, color="black", lw=0.8)
    axes[1, 1].set_xlabel("Time (ps)")
    axes[1, 1].set_ylabel("Pressure (GPa)")
    axes[1, 1].set_title("Pressure")

    fig.savefig(out / "thermo_history.png", dpi=220)
    plt.close(fig)

    tail = thermo.tail(min(len(thermo), 51))
    return {
        "final_temp_K": float(thermo.iloc[-1]["temp_K"]),
        "final_density_g_cm3": float(thermo.iloc[-1]["density_g_cm3"]),
        "final_pressure_GPa": float(thermo.iloc[-1]["press_bar"] * 1.0e-4),
        "tail_temp_K": float(tail["temp_K"].mean()),
        "tail_density_g_cm3": float(tail["density_g_cm3"].mean()),
        "tail_pressure_GPa": float(tail["press_bar"].mean() * 1.0e-4),
        "tail_pe_per_atom_eV": float(tail["pe_per_atom_eV"].mean()),
    }


def save_rdf(dump_path: Path, out: Path) -> None:
    pipeline = import_file(str(dump_path))
    pipeline.modifiers.append(PythonScriptModifier(function=configure_types))
    pipeline.modifiers.append(
        CoordinationAnalysisModifier(
            cutoff=8.0,
            number_of_bins=200,
            partial=True,
        )
    )
    export_file(pipeline, str(out / "rdf_partial.csv"), "txt/table", key="coordination-rdf")

    rdf = pd.read_csv(
        out / "rdf_partial.csv",
        comment="#",
        sep=r"\s+",
        header=None,
        names=["r_A", "Cu-Cu", "Cu-Zr", "Zr-Zr"],
    )
    rdf.to_csv(out / "rdf_partial_named.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for col in rdf.columns[1:]:
        ax.plot(rdf["r_A"], rdf[col], lw=1.3, label=col)
    ax.set_xlabel("r (Angstrom)")
    ax.set_ylabel("g(r)")
    ax.set_title("Partial RDF")
    ax.legend(frameon=False, fontsize=9)
    fig.savefig(out / "rdf_partial.png", dpi=220)
    plt.close(fig)


def compute_voronoi_atoms(dump_path: Path, threshold: float) -> pd.DataFrame:
    pipeline = import_file(str(dump_path))
    pipeline.modifiers.append(PythonScriptModifier(function=configure_types))
    pipeline.modifiers.append(
        VoronoiAnalysisModifier(
            compute_indices=True,
            use_radii=True,
            edge_threshold=threshold,
            face_threshold=threshold,
        )
    )
    data = pipeline.compute()

    ptype = np.asarray(data.particles["Particle Type"], dtype=int)
    volume = np.asarray(data.particles["Atomic Volume"], dtype=float)
    coordination = np.asarray(data.particles["Coordination"], dtype=int)
    vindex = np.asarray(data.particles["Voronoi Index"], dtype=int)

    atoms = pd.DataFrame(
        {
            "type": ptype,
            "element": [TYPE_NAMES[int(t)] for t in ptype],
            "atomic_volume_A3": volume,
            "coordination": coordination,
        }
    )
    for i in range(min(vindex.shape[1], 12)):
        atoms[f"n{i + 1}"] = vindex[:, i]

    # OVITO stores n1,n2,n3,...; metallic-glass convention uses <n3,n4,n5,n6>.
    atoms["n3_conv"] = vindex[:, 2]
    atoms["n4_conv"] = vindex[:, 3]
    atoms["n5_conv"] = vindex[:, 4]
    atoms["n6_conv"] = vindex[:, 5]
    atoms["voronoi_index"] = [
        f"<{n3},{n4},{n5},{n6}>"
        for n3, n4, n5, n6 in zip(
            atoms["n3_conv"],
            atoms["n4_conv"],
            atoms["n5_conv"],
            atoms["n6_conv"],
        )
    ]
    atoms["is_full_icosahedron_00120"] = atoms["voronoi_index"] == "<0,0,12,0>"
    atoms["is_cn12_ico_like_n5_ge8"] = (atoms["coordination"] == 12) & (atoms["n5_conv"] >= 8)
    atoms["is_fivefold_rich_n5_ge10"] = atoms["n5_conv"] >= 10
    return atoms


def top_motifs(atoms: pd.DataFrame, group_column: str | None = None) -> pd.DataFrame:
    rows = []
    groups = [("all", atoms)] if group_column is None else list(atoms.groupby(group_column))
    for group_name, group in groups:
        counts = Counter(group["voronoi_index"])
        for rank, (index, count) in enumerate(counts.most_common(40), start=1):
            n3, n4, n5, n6 = [int(x) for x in index.strip("<>").split(",")]
            rows.append(
                {
                    "scope": group_name,
                    "rank": rank,
                    "voronoi_index": index,
                    "n3": n3,
                    "n4": n4,
                    "n5": n5,
                    "n6": n6,
                    "count": int(count),
                    "fraction": float(count / len(group)),
                }
            )
    return pd.DataFrame(rows)


def family_stats(atoms: pd.DataFrame, threshold: float) -> pd.DataFrame:
    rows = []
    scopes = [("all", atoms)] + [(name, group) for name, group in atoms.groupby("element")]
    families = {
        "full_icosahedron_00120": "is_full_icosahedron_00120",
        "cn12_ico_like_n5_ge8": "is_cn12_ico_like_n5_ge8",
        "fivefold_rich_n5_ge10": "is_fivefold_rich_n5_ge10",
    }
    for scope, group in scopes:
        for family, column in families.items():
            count = int(group[column].sum())
            rows.append(
                {
                    "threshold": threshold,
                    "scope": scope,
                    "family": family,
                    "count": count,
                    "fraction": float(count / len(group)),
                }
            )
    return pd.DataFrame(rows)


def rank_of(top: pd.DataFrame, scope: str, index: str) -> int | None:
    hit = top[(top["scope"] == scope) & (top["voronoi_index"] == index)]
    if hit.empty:
        return None
    return int(hit.iloc[0]["rank"])


def plot_primary(atoms: pd.DataFrame, top_global: pd.DataFrame, top_by_element: pd.DataFrame, families: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
    top_plot = top_global[top_global["scope"] == "all"].head(15).iloc[::-1]
    colors = ["#b85c38" if idx == "<0,0,12,0>" else "#4f7f9f" for idx in top_plot["voronoi_index"]]
    ax.barh(top_plot["voronoi_index"], top_plot["fraction"], color=colors)
    ax.set_xlabel("Fraction")
    ax.set_title("Top Voronoi indices, all centers")
    fig.savefig(out / "voronoi_top15_all_centers.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), constrained_layout=True)
    for ax, elem in zip(axes, ["Cu", "Zr"]):
        sub = top_by_element[top_by_element["scope"] == elem].head(12).iloc[::-1]
        colors = ["#b85c38" if idx == "<0,0,12,0>" else "#4f7f9f" for idx in sub["voronoi_index"]]
        ax.barh(sub["voronoi_index"], sub["fraction"], color=colors)
        ax.set_title(f"{elem}-centered Voronoi motifs")
        ax.set_xlabel("Fraction within element")
    fig.savefig(out / "voronoi_by_element_top12.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.8), constrained_layout=True)
    family_plot = families[families["scope"].isin(["Cu", "Zr"])].copy()
    family_plot["label"] = family_plot["family"].map(
        {
            "full_icosahedron_00120": "Full ico <0,0,12,0>",
            "cn12_ico_like_n5_ge8": "CN12 ico-like n5>=8",
            "fivefold_rich_n5_ge10": "Fivefold-rich n5>=10",
        }
    )
    pivot = family_plot.pivot(index="label", columns="scope", values="fraction")
    pivot.plot(kind="bar", ax=ax, width=0.78, color=["#b85c38", "#4f7f9f"])
    ax.set_xlabel("")
    ax.set_ylabel("Fraction within element")
    ax.set_title("Robust motif-family statistics")
    ax.tick_params(axis="x", rotation=15)
    ax.legend(frameon=False)
    fig.savefig(out / "voronoi_family_stats.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
    cn_stats = atoms.groupby(["element", "coordination"]).size().reset_index(name="count")
    cn_stats["fraction_within_element"] = cn_stats["count"] / cn_stats.groupby("element")["count"].transform("sum")
    cn_pivot = cn_stats.pivot(index="coordination", columns="element", values="fraction_within_element").fillna(0)
    cn_pivot.plot(kind="bar", ax=ax, width=0.82)
    ax.set_xlabel("Coordination number")
    ax.set_ylabel("Fraction within element")
    ax.set_title("Coordination distribution")
    ax.legend(frameon=False)
    fig.savefig(out / "coordination_distribution.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
    for element, group in atoms.groupby("element"):
        ax.hist(group["atomic_volume_A3"], bins=45, alpha=0.55, density=True, label=element)
    ax.set_xlabel("Atomic volume (Angstrom^3)")
    ax.set_ylabel("Probability density")
    ax.set_title("Atomic volume distribution")
    ax.legend(frameon=False)
    fig.savefig(out / "atomic_volume_distribution.png", dpi=220)
    plt.close(fig)


def plot_threshold_sensitivity(all_families: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5.6), constrained_layout=True)
    sub = all_families[
        (all_families["scope"] == "Cu")
        & (all_families["family"].isin(["full_icosahedron_00120", "cn12_ico_like_n5_ge8"]))
    ].copy()
    labels = {
        "full_icosahedron_00120": "Full ico <0,0,12,0>",
        "cn12_ico_like_n5_ge8": "CN12 ico-like n5>=8",
    }
    for family, group in sub.groupby("family"):
        group = group.sort_values("threshold")
        ax.plot(group["threshold"], group["fraction"], marker="o", lw=1.8, label=labels[family])
    ax.set_xlabel("Voronoi edge/face threshold")
    ax.set_ylabel("Fraction within Cu-centered atoms")
    ax.set_title("Threshold sensitivity, Cu-centered motifs")
    ax.legend(frameon=False)
    fig.savefig(out / "voronoi_threshold_sensitivity_cu.png", dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="N10000", help="File tag such as N5000 or N10000.")
    parser.add_argument("--root", default=str(ROOT), help="LAMMPS project directory.")
    parser.add_argument("--primary-threshold", type=float, default=PRIMARY_THRESHOLD)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = root / f"analysis_{args.tag}"
    out.mkdir(exist_ok=True)
    dump_path = root / "dumps" / f"Glass_Cu50Zr50_{args.tag}_300K_equilibrated.dump"
    thermo_path = root / "observables" / f"ZrCu_Cu50Zr50_{args.tag}_thermo.dat"
    if not dump_path.exists():
        raise FileNotFoundError(f"Dump file not found: {dump_path}")
    if not thermo_path.exists():
        raise FileNotFoundError(f"Thermo file not found: {thermo_path}")

    summary = save_thermo_plots(load_thermo(thermo_path), out)
    save_rdf(dump_path, out)

    all_families = []
    primary_atoms = None
    primary_top_global = None
    primary_top_by_element = None
    primary_families = None

    for threshold in THRESHOLDS:
        atoms = compute_voronoi_atoms(dump_path, threshold)
        suffix = f"thr{int(round(threshold * 100)):03d}"
        atoms.to_csv(out / f"voronoi_per_atom_{suffix}.csv", index=False)

        top_global = top_motifs(atoms)
        top_by_element = top_motifs(atoms, "element")
        families = family_stats(atoms, threshold)

        top_global.to_csv(out / f"voronoi_top40_all_centers_{suffix}.csv", index=False)
        top_by_element.to_csv(out / f"voronoi_top40_by_element_{suffix}.csv", index=False)
        families.to_csv(out / f"voronoi_family_stats_{suffix}.csv", index=False)
        all_families.append(families)

        if abs(threshold - args.primary_threshold) < 1.0e-12:
            primary_atoms = atoms
            primary_top_global = top_global
            primary_top_by_element = top_by_element
            primary_families = families

    if primary_atoms is None or primary_top_global is None or primary_top_by_element is None or primary_families is None:
        raise ValueError(f"Primary threshold {args.primary_threshold} is not in {THRESHOLDS}")

    all_families_df = pd.concat(all_families, ignore_index=True)
    all_families_df.to_csv(out / "voronoi_family_stats_threshold_sensitivity.csv", index=False)

    plot_primary(primary_atoms, primary_top_global, primary_top_by_element, primary_families, out)
    plot_threshold_sensitivity(all_families_df, out)

    vol_stats = primary_atoms.groupby("element")["atomic_volume_A3"].describe()
    vol_stats.to_csv(out / "atomic_volume_by_element.csv")
    cn_stats = primary_atoms.groupby(["element", "coordination"]).size().reset_index(name="count")
    cn_stats["fraction_within_element"] = cn_stats["count"] / cn_stats.groupby("element")["count"].transform("sum")
    cn_stats.to_csv(out / "coordination_by_element.csv", index=False)

    cu_family = primary_families[(primary_families["scope"] == "Cu")].set_index("family")
    all_family = primary_families[(primary_families["scope"] == "all")].set_index("family")

    summary.update(
        {
            "num_atoms": int(len(primary_atoms)),
            "mean_coordination": float(primary_atoms["coordination"].mean()),
            "mean_atomic_volume_A3": float(primary_atoms["atomic_volume_A3"].mean()),
            "cu_mean_atomic_volume_A3": float(primary_atoms.loc[primary_atoms["element"] == "Cu", "atomic_volume_A3"].mean()),
            "zr_mean_atomic_volume_A3": float(primary_atoms.loc[primary_atoms["element"] == "Zr", "atomic_volume_A3"].mean()),
            "all_00120_fraction": float(all_family.loc["full_icosahedron_00120", "fraction"]),
            "cu_00120_fraction": float(cu_family.loc["full_icosahedron_00120", "fraction"]),
            "cu_cn12_ico_like_n5_ge8_fraction": float(cu_family.loc["cn12_ico_like_n5_ge8", "fraction"]),
            "cu_fivefold_rich_n5_ge10_fraction": float(cu_family.loc["fivefold_rich_n5_ge10", "fraction"]),
            "all_00120_rank": rank_of(primary_top_global, "all", "<0,0,12,0>"),
            "cu_00120_rank": rank_of(primary_top_by_element, "Cu", "<0,0,12,0>"),
        }
    )
    pd.DataFrame([summary]).to_csv(out / "structure_summary.csv", index=False)

    lines = [f"# Cu50Zr50 Robust Structural Analysis {args.tag}", ""]
    lines.append(f"Primary Voronoi threshold: edge_threshold = face_threshold = {args.primary_threshold:g}")
    lines.append("")
    for key, value in summary.items():
        if isinstance(value, float):
            lines.append(f"- {key}: {value:.6g}")
        else:
            lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("Primary top Cu-centered motifs:")
    for _, row in primary_top_by_element[primary_top_by_element["scope"] == "Cu"].head(8).iterrows():
        lines.append(f"- rank {int(row['rank'])}: {row['voronoi_index']} = {row['fraction']:.4%}")
    lines.append("")
    lines.append("Generated files:")
    for path in sorted(out.glob("*")):
        lines.append(f"- {path.name}")
    (out / "structure_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print((out / "structure_summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
