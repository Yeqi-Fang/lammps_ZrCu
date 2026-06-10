from __future__ import annotations

import numpy as np
import pandas as pd


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

df = pd.read_csv(
    "observables/ZrCu_Cu50Zr50_N5000_thermo.dat",
    comment="#",
    sep=r"\s+",
    names=names,
)

windows = {
    "melt_2000K_last_50ps": df[(df.step >= 50000) & (df.step <= 100000)],
    "final_300K_50ps": df[(df.step >= 440000) & (df.step <= 490000)],
    "final_300K_last_25ps": df[(df.step >= 465000) & (df.step <= 490000)],
}

for label, sub in windows.items():
    print(f"\n{label} n={len(sub)}")
    for col in ["temp_K", "press_bar", "density_g_cm3", "pe_per_atom_eV", "vol_per_atom_A3"]:
        mean = sub[col].mean()
        std = sub[col].std(ddof=1)
        print(f"{col}: mean={mean:.8g} std={std:.5g}")
    if len(sub) > 2:
        x = sub.time_ps.to_numpy()
        for col in ["density_g_cm3", "pe_per_atom_eV", "press_bar"]:
            slope = np.polyfit(x, sub[col].to_numpy(), 1)[0]
            print(f"slope {col} per ps: {slope:.5g}")

sub = df[(df.step >= 440000) & (df.step <= 490000)].copy()
sub["block"] = ((sub.time_ps - 440) // 10).astype(int)
print("\n10 ps blocks final equilibrium:")
print(
    sub.groupby("block")[["temp_K", "density_g_cm3", "pe_per_atom_eV", "press_bar"]]
    .mean()
    .to_string()
)
