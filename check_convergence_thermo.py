from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent

THERMO_NAMES = [
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


def slope_per_ps(frame: pd.DataFrame, column: str) -> float:
    if len(frame) < 2:
        return float("nan")
    return float(np.polyfit(frame["time_ps"], frame[column], 1)[0])


def summarize_window(name: str, frame: pd.DataFrame) -> list[dict[str, float | str | int]]:
    rows = []
    for column in ["temp_K", "press_bar", "density_g_cm3", "pe_per_atom_eV"]:
        rows.append(
            {
                "window": name,
                "property": column,
                "n": int(len(frame)),
                "mean": float(frame[column].mean()),
                "std": float(frame[column].std(ddof=1)),
                "slope_per_ps": slope_per_ps(frame, column),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="N10000", help="File tag such as N5000 or N10000.")
    parser.add_argument("--root", default=str(ROOT), help="LAMMPS project directory.")
    parser.add_argument("--melt-steps", type=int, default=100000)
    parser.add_argument("--quench-steps", type=int, default=340000)
    parser.add_argument("--eq-steps", type=int, default=50000)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = root / f"analysis_{args.tag}"
    out.mkdir(exist_ok=True)
    thermo_path = root / "observables" / f"ZrCu_Cu50Zr50_{args.tag}_thermo.dat"
    if not thermo_path.exists():
        raise FileNotFoundError(f"Thermo file not found: {thermo_path}")

    thermo = pd.read_csv(thermo_path, comment="#", sep=r"\s+", names=THERMO_NAMES)
    thermo.to_csv(out / "thermo_history.csv", index=False)

    melt_end = args.melt_steps
    final_end = args.melt_steps + args.quench_steps + args.eq_steps
    eq_start = args.melt_steps + args.quench_steps

    eq_duration_ps = args.eq_steps // 1000
    windows = {
        "melt_last_50ps": thermo[(thermo["step"] >= melt_end - 50000) & (thermo["step"] <= melt_end)],
        f"final_300K_all_{eq_duration_ps}ps": thermo[(thermo["step"] >= eq_start) & (thermo["step"] <= final_end)],
        "final_300K_last_25ps": thermo[(thermo["step"] >= final_end - 25000) & (thermo["step"] <= final_end)],
    }

    rows: list[dict[str, float | str | int]] = []
    for name, frame in windows.items():
        rows.extend(summarize_window(name, frame))
    summary = pd.DataFrame(rows)
    summary.to_csv(out / "convergence_summary.csv", index=False)

    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    plot_columns = [
        ("temp_K", "Temperature (K)"),
        ("density_g_cm3", "Density (g/cm3)"),
        ("pe_per_atom_eV", "PE/atom (eV)"),
        ("press_bar", "Pressure (bar)"),
    ]
    for ax, (column, ylabel) in zip(axes.ravel(), plot_columns):
        ax.plot(thermo["time_ps"], thermo[column], lw=1.0)
        ax.axvspan(eq_start * 0.001, final_end * 0.001, color="#d8e8d4", alpha=0.35, lw=0)
        ax.set_xlabel("Time (ps)")
        ax.set_ylabel(ylabel)
    fig.savefig(out / "convergence_history.png", dpi=220)
    plt.close(fig)

    lines = [f"# Convergence Summary {args.tag}", ""]
    for _, row in summary.iterrows():
        lines.append(
            f"- {row['window']} {row['property']}: "
            f"mean={row['mean']:.6g}, std={row['std']:.6g}, slope/ps={row['slope_per_ps']:.6g}"
        )
    (out / "convergence_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print((out / "convergence_summary.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
