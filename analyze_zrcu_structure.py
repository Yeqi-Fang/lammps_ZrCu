from __future__ import annotations

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
OUT = ROOT / "analysis"
OUT.mkdir(exist_ok=True)

DUMP_300K = ROOT / "dumps" / "Glass_Cu50Zr50_N5000_300K_equilibrated.dump"
THERMO = ROOT / "observables" / "ZrCu_Cu50Zr50_N5000_thermo.dat"

TYPE_NAMES = {1: "Cu", 2: "Zr"}
TYPE_RADII = {1: 1.35, 2: 1.55}


def configure_types(frame, data):
    types = data.particles_.particle_types_
    for type_id, name in TYPE_NAMES.items():
        particle_type = types.type_by_id_(type_id)
        particle_type.name = name
        particle_type.radius = TYPE_RADII.get(type_id, 1.45)


def load_thermo() -> pd.DataFrame:
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
    return pd.read_csv(THERMO, comment="#", sep=r"\s+", names=names)


def save_thermo_plots() -> dict[str, float]:
    thermo = load_thermo()
    thermo.to_csv(OUT / "thermo_history.csv", index=False)

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

    fig.savefig(OUT / "thermo_history.png", dpi=220)
    plt.close(fig)

    tail = thermo[thermo["step"] >= 440000]
    return {
        "final_temp_K": float(thermo.iloc[-1]["temp_K"]),
        "final_density_g_cm3": float(thermo.iloc[-1]["density_g_cm3"]),
        "final_pressure_GPa": float(thermo.iloc[-1]["press_bar"] * 1.0e-4),
        "avg_300K_temp_K": float(tail["temp_K"].mean()),
        "avg_300K_density_g_cm3": float(tail["density_g_cm3"].mean()),
        "avg_300K_pressure_GPa": float(tail["press_bar"].mean() * 1.0e-4),
        "avg_300K_pe_per_atom_eV": float(tail["pe_per_atom_eV"].mean()),
    }


def analyze_structure() -> dict[str, float | int]:
    pipeline = import_file(str(DUMP_300K))
    pipeline.modifiers.append(PythonScriptModifier(function=configure_types))

    pipeline.modifiers.append(
        CoordinationAnalysisModifier(
            cutoff=8.0,
            number_of_bins=200,
            partial=True,
        )
    )
    export_file(pipeline, str(OUT / "rdf_partial.csv"), "txt/table", key="coordination-rdf")

    pipeline.modifiers.append(
        VoronoiAnalysisModifier(
            compute_indices=True,
            use_radii=True,
            edge_threshold=0.1,
            face_threshold=0.1,
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

    atoms.to_csv(OUT / "voronoi_per_atom.csv", index=False)

    # OVITO's Voronoi Index vector stores n1,n2,n3,...; the metallic-glass
    # convention <n3,n4,n5,n6> therefore corresponds to columns 2:6.
    idx4 = [tuple(row[2:6]) for row in vindex]
    counter4 = Counter(idx4)
    top_rows = []
    for index, count in counter4.most_common(40):
        top_rows.append(
            {
                "voronoi_index": f"<{index[0]},{index[1]},{index[2]},{index[3]}>",
                "n3": index[0],
                "n4": index[1],
                "n5": index[2],
                "n6": index[3],
                "count": count,
                "fraction": count / len(idx4),
            }
        )
    top = pd.DataFrame(top_rows)
    top.to_csv(OUT / "voronoi_top40.csv", index=False)

    vol_stats = atoms.groupby("element")["atomic_volume_A3"].describe()
    vol_stats.to_csv(OUT / "atomic_volume_by_element.csv")
    cn_stats = atoms.groupby(["element", "coordination"]).size().reset_index(name="count")
    cn_stats["fraction_within_element"] = cn_stats["count"] / cn_stats.groupby("element")["count"].transform("sum")
    cn_stats.to_csv(OUT / "coordination_by_element.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)
    rdf = pd.read_csv(
        OUT / "rdf_partial.csv",
        comment="#",
        sep=r"\s+",
        header=None,
        names=["r_A", "Cu-Cu", "Cu-Zr", "Zr-Zr"],
    )
    rdf.to_csv(OUT / "rdf_partial_named.csv", index=False)
    x = rdf.iloc[:, 0]
    for col in rdf.columns[1:]:
        ax.plot(x, rdf[col], lw=1.3, label=col)
    ax.set_xlabel("r (Angstrom)")
    ax.set_ylabel("g(r)")
    ax.set_title("Partial RDF")
    ax.legend(frameon=False, fontsize=9)
    fig.savefig(OUT / "rdf_partial.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
    for element, group in atoms.groupby("element"):
        ax.hist(group["atomic_volume_A3"], bins=40, alpha=0.55, density=True, label=element)
    ax.set_xlabel("Atomic volume (Angstrom^3)")
    ax.set_ylabel("Probability density")
    ax.set_title("Atomic Volume Distribution")
    ax.legend(frameon=False)
    fig.savefig(OUT / "atomic_volume_distribution.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5), constrained_layout=True)
    cn_pivot = cn_stats.pivot(index="coordination", columns="element", values="fraction_within_element").fillna(0)
    cn_pivot.plot(kind="bar", ax=ax, width=0.82)
    ax.set_xlabel("Coordination number")
    ax.set_ylabel("Fraction within element")
    ax.set_title("Coordination Distribution")
    ax.legend(frameon=False)
    fig.savefig(OUT / "coordination_distribution.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)
    top_plot = top.head(15).iloc[::-1]
    ax.barh(top_plot["voronoi_index"], top_plot["fraction"], color="#4f7f9f")
    ax.set_xlabel("Fraction")
    ax.set_title("Top Voronoi Indices")
    fig.savefig(OUT / "voronoi_top15.png", dpi=220)
    plt.close(fig)

    ico_count = counter4.get((0, 0, 12, 0), 0)
    z16_like = sum(count for idx, count in counter4.items() if idx[2] >= 10)

    summary = {
        "num_atoms": int(len(atoms)),
        "mean_coordination": float(atoms["coordination"].mean()),
        "mean_atomic_volume_A3": float(atoms["atomic_volume_A3"].mean()),
        "cu_mean_atomic_volume_A3": float(atoms.loc[atoms["element"] == "Cu", "atomic_volume_A3"].mean()),
        "zr_mean_atomic_volume_A3": float(atoms.loc[atoms["element"] == "Zr", "atomic_volume_A3"].mean()),
        "icosahedron_00120_count": int(ico_count),
        "icosahedron_00120_fraction": float(ico_count / len(atoms)),
        "high_n5_fraction": float(z16_like / len(atoms)),
    }
    return summary


def main() -> None:
    summary = {}
    summary.update(save_thermo_plots())
    summary.update(analyze_structure())

    summary_path = OUT / "structure_summary.csv"
    pd.DataFrame([summary]).to_csv(summary_path, index=False)

    lines = ["# Cu50Zr50 Structural Analysis Summary", ""]
    for key, value in summary.items():
        if isinstance(value, float):
            lines.append(f"- {key}: {value:.6g}")
        else:
            lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("Generated files:")
    for path in sorted(OUT.glob("*")):
        lines.append(f"- {path.name}")
    (OUT / "structure_summary.md").write_text("\n".join(lines), encoding="utf-8")

    print((OUT / "structure_summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
