from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "analysis" / "moduli"


def linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def load_shear(component: str) -> pd.DataFrame:
    shear = pd.read_csv(
        OUT / f"shear_{component}_stress.dat",
        comment="#",
        sep=r"\s+",
        names=["gamma", "tau_GPa", "pij_GPa", "pe_per_atom_eV", "vol_A3", "tilt_A"],
    )
    shear["component"] = component
    return shear


def main() -> None:
    global OUT

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT), help="Directory containing stress files and receiving fit outputs.")
    args = parser.parse_args()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    OUT = out_path.resolve()
    OUT.mkdir(parents=True, exist_ok=True)

    shear_frames = []
    shear_results = []
    for component in ["xy", "xz", "yz"]:
        path = OUT / f"shear_{component}_stress.dat"
        if not path.exists():
            continue
        shear = load_shear(component).sort_values("gamma")
        shear_fit = shear[(shear["gamma"].abs() <= 0.004) & (shear["gamma"].abs() > 0)]
        G_i, tau0_i = linear_fit(shear_fit["gamma"].to_numpy(), shear_fit["tau_GPa"].to_numpy())
        shear["fit_G_GPa"] = G_i
        shear["fit_intercept_GPa"] = tau0_i
        shear_frames.append(shear)
        shear_results.append(
            {
                "component": component,
                "shear_modulus_G_GPa": G_i,
                "fit_intercept_GPa": tau0_i,
                "fit_points": len(shear_fit),
            }
        )

        fig, ax = plt.subplots(figsize=(7.5, 5.2), constrained_layout=True)
        ax.scatter(shear["gamma"], shear["tau_GPa"], s=36, color="#4f7f9f", label="LAMMPS")
        xs = np.linspace(shear_fit["gamma"].min(), shear_fit["gamma"].max(), 100)
        ax.plot(xs, G_i * xs + tau0_i, color="#222222", lw=1.5, label=f"fit G={G_i:.1f} GPa")
        ax.axhline(0, color="black", lw=0.7)
        ax.axvline(0, color="black", lw=0.7)
        ax.set_xlabel(f"Shear strain gamma_{component}")
        ax.set_ylabel(f"Shear stress -P{component} (GPa)")
        ax.set_title(f"0 K AQS Shear Modulus {component}")
        ax.legend(frameon=False)
        fig.savefig(OUT / f"shear_modulus_{component}_fit.png", dpi=220)
        if component == "xy":
            fig.savefig(OUT / "shear_modulus_fit.png", dpi=220)
        plt.close(fig)

    if not shear_results:
        raise RuntimeError("No shear stress files found.")

    shear_all = pd.concat(shear_frames, ignore_index=True)
    zero_tau = (
        shear_all.loc[shear_all["gamma"].abs() < 1.0e-12, ["component", "tau_GPa"]]
        .set_index("component")["tau_GPa"]
        .to_dict()
    )
    shear_all["tau_residual_GPa"] = shear_all["component"].map(zero_tau)
    shear_all["tau_delta_GPa"] = shear_all["tau_GPa"] - shear_all["tau_residual_GPa"]
    shear_all.to_csv(OUT / "shear_all_components.csv", index=False)
    shear_by_component = pd.DataFrame(shear_results)
    shear_by_component.to_csv(OUT / "shear_moduli_by_component.csv", index=False)

    G = float(shear_by_component["shear_modulus_G_GPa"].mean())
    G_std = float(shear_by_component["shear_modulus_G_GPa"].std(ddof=0))

    bulk = pd.read_csv(
        OUT / "bulk_stress.dat",
        comment="#",
        sep=r"\s+",
        names=["eta", "hydro_GPa", "press_GPa", "pe_per_atom_eV", "vol_A3", "density_g_cm3"],
    )

    bulk = bulk.sort_values("eta")

    bulk_fit = bulk[(bulk["eta"].abs() <= 0.004) & (bulk["eta"].abs() > 0)]

    K, h0 = linear_fit(bulk_fit["eta"].to_numpy(), bulk_fit["hydro_GPa"].to_numpy())
    E = 9.0 * K * G / (3.0 * K + G)
    nu = (3.0 * K - 2.0 * G) / (2.0 * (3.0 * K + G))

    fig, ax = plt.subplots(figsize=(8.2, 5.4), constrained_layout=True)
    colors = {"xy": "#4f7f9f", "xz": "#7b6ba8", "yz": "#6f8b3d"}
    for component, group in shear_all.groupby("component"):
        ax.scatter(group["gamma"], group["tau_GPa"], s=32, color=colors.get(component), label=f"{component}")
        fit = shear_by_component[shear_by_component["component"] == component].iloc[0]
        xs = np.linspace(-0.004, 0.004, 100)
        ax.plot(xs, fit["shear_modulus_G_GPa"] * xs + fit["fit_intercept_GPa"], color=colors.get(component), lw=1.2)
    ax.axhline(0, color="black", lw=0.7)
    ax.axvline(0, color="black", lw=0.7)
    ax.set_xlabel("Shear strain gamma")
    ax.set_ylabel("Shear stress -Pij (GPa)")
    ax.set_title(f"0 K AQS Shear Moduli, average G={G:.1f} GPa")
    ax.legend(frameon=False)
    fig.savefig(OUT / "shear_moduli_all_components.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.2, 5.4), constrained_layout=True)
    for component, group in shear_all.groupby("component"):
        ax.scatter(group["gamma"], group["tau_delta_GPa"], s=32, color=colors.get(component), label=f"{component}")
        fit = shear_by_component[shear_by_component["component"] == component].iloc[0]
        xs = np.linspace(-0.004, 0.004, 100)
        ax.plot(xs, fit["shear_modulus_G_GPa"] * xs, color=colors.get(component), lw=1.2)
    ax.axhline(0, color="black", lw=0.7)
    ax.axvline(0, color="black", lw=0.7)
    ax.set_xlabel("Shear strain gamma")
    ax.set_ylabel("Shear stress change Delta(-Pij) (GPa)")
    ax.set_title(f"Residual-Subtracted Shear Response, average G={G:.1f} GPa")
    ax.legend(frameon=False)
    fig.savefig(OUT / "shear_moduli_residual_subtracted.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 5.2), constrained_layout=True)
    ax.scatter(bulk["eta"], bulk["hydro_GPa"], s=36, color="#8b6f3d", label="LAMMPS")
    xs = np.linspace(bulk_fit["eta"].min(), bulk_fit["eta"].max(), 100)
    ax.plot(xs, K * xs + h0, color="#222222", lw=1.5, label=f"fit K={K:.1f} GPa")
    ax.axhline(0, color="black", lw=0.7)
    ax.axvline(0, color="black", lw=0.7)
    ax.set_xlabel("Volumetric strain dV/V")
    ax.set_ylabel("Hydrostatic tensile stress -P (GPa)")
    ax.set_title("0 K Bulk Modulus")
    ax.legend(frameon=False)
    fig.savefig(OUT / "bulk_modulus_fit.png", dpi=220)
    plt.close(fig)

    summary = pd.DataFrame(
        [
            {
                "bulk_modulus_K_GPa": K,
                "shear_modulus_G_avg_GPa": G,
                "shear_modulus_G_std_GPa": G_std,
                "young_modulus_E_GPa": E,
                "poisson_ratio_nu": nu,
                "bulk_fit_intercept_GPa": h0,
                "shear_components": len(shear_by_component),
                "bulk_fit_points": len(bulk_fit),
            }
        ]
    )
    summary.to_csv(OUT / "moduli_summary.csv", index=False)

    lines = [
        "# 0 K Elastic Modulus Summary",
        "",
        f"- Bulk modulus K: {K:.3f} GPa",
        f"- Shear modulus G, average over available shear directions: {G:.3f} GPa",
        f"- Shear modulus direction-to-direction std: {G_std:.3f} GPa",
        f"- Young modulus E, isotropic estimate: {E:.3f} GPa",
        f"- Poisson ratio nu, isotropic estimate: {nu:.4f}",
        "",
        "Shear components:",
        *(f"- G_{row.component}: {row.shear_modulus_G_GPa:.3f} GPa" for row in shear_by_component.itertuples()),
        "",
        "Fit window: |strain| <= 0.004, excluding zero strain.",
        "",
        "Generated files:",
        "- shear_xy_stress.dat / shear_xz_stress.dat / shear_yz_stress.dat",
        "- bulk_stress.dat",
        "- shear_moduli_all_components.png",
        "- bulk_modulus_fit.png",
        "- moduli_summary.csv",
    ]
    (OUT / "moduli_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
