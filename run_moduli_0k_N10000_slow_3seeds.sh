#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]]; then
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [[ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]]; then
  source "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [[ -f "$HOME/miniforge3/etc/profile.d/conda.sh" ]]; then
  source "$HOME/miniforge3/etc/profile.d/conda.sh"
else
  echo "Conda shell hook was not found."
  exit 127
fi
conda activate lammps

NP="${NP:-8}"
RESUME="${RESUME:-1}"
START_SEED="${START_SEED:-1}"
END_SEED="${END_SEED:-3}"
export OMP_NUM_THREADS=1

TAGS=(
  N10000_seed1_q1e12
  N10000_seed2_q1e12
  N10000_seed3_q1e12
)

run_one_tag() {
  local tag="$1"
  local outdir="analysis_${tag}/moduli"
  local final_sample="samples/Glass_Cu50Zr50_${tag}_0K_minimized.dat"

  if [[ ! -s "$final_sample" ]]; then
    echo "Skipping ${tag}: ${final_sample} is missing."
    return
  fi

  mkdir -p "$outdir"

  if [[ "$RESUME" == "1" && -s "${outdir}/moduli_summary.csv" ]]; then
    echo "Skipping ${tag}: ${outdir}/moduli_summary.csv already exists."
    return
  fi

  echo "Relaxing zero-pressure state for ${tag}"
  mpirun -np "${NP}" lmp -screen none -in relax_zeroP_0k_tagged.lmp -var run_tag "$tag" -log "${outdir}/relax_zeroP_0k.log"

  cat > "${outdir}/shear_xy_stress.dat" <<'EOF'
# gamma tau_GPa pxy_GPa pe_per_atom_eV vol_A3 xy_A
EOF
  cat > "${outdir}/shear_xz_stress.dat" <<'EOF'
# gamma tau_GPa pxz_GPa pe_per_atom_eV vol_A3 xz_A
EOF
  cat > "${outdir}/shear_yz_stress.dat" <<'EOF'
# gamma tau_GPa pyz_GPa pe_per_atom_eV vol_A3 yz_A
EOF
  cat > "${outdir}/bulk_stress.dat" <<'EOF'
# eta hydro_GPa press_GPa pe_per_atom_eV vol_A3 density_g_cm3
EOF

  for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
    echo "${tag}: xy shear strain ${strain}"
    mpirun -np "${NP}" lmp -screen none -in modulus_shear_xy_0k_tagged.lmp -var run_tag "$tag" -var strain "${strain}" -log "${outdir}/shear_xy_${strain}.log"
  done

  for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
    echo "${tag}: xz shear strain ${strain}"
    mpirun -np "${NP}" lmp -screen none -in modulus_shear_xz_0k_tagged.lmp -var run_tag "$tag" -var strain "${strain}" -log "${outdir}/shear_xz_${strain}.log"
  done

  for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
    echo "${tag}: yz shear strain ${strain}"
    mpirun -np "${NP}" lmp -screen none -in modulus_shear_yz_0k_tagged.lmp -var run_tag "$tag" -var strain "${strain}" -log "${outdir}/shear_yz_${strain}.log"
  done

  for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
    echo "${tag}: bulk strain ${strain}"
    mpirun -np "${NP}" lmp -screen none -in modulus_bulk_0k_tagged.lmp -var run_tag "$tag" -var strain "${strain}" -log "${outdir}/bulk_${strain}.log"
  done

  conda activate ovito
  python fit_moduli.py --out "$outdir"
  conda activate lammps
}

for i in "${!TAGS[@]}"; do
  seed_index=$((i + 1))
  if (( seed_index < START_SEED || seed_index > END_SEED )); then
    continue
  fi
  run_one_tag "${TAGS[$i]}"
done
