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

conda activate ovito

TAGS=(
  N10000_seed1_q1e12
  N10000_seed2_q1e12
  N10000_seed3_q1e12
)

for tag in "${TAGS[@]}"; do
  dump="dumps/Glass_Cu50Zr50_${tag}_300K_equilibrated.dump"
  if [[ ! -s "$dump" ]]; then
    echo "Skipping ${tag}: ${dump} is missing."
    continue
  fi

  echo "Analyzing ${tag}"
  python analyze_zrcu_structure_robust.py --tag "$tag"
  python check_convergence_thermo.py --tag "$tag" --melt-steps 100000 --quench-steps 1700000 --eq-steps 100000
done

python aggregate_seed_analyses.py --tags "${TAGS[@]}" --out analysis_N10000_slow_3seeds
