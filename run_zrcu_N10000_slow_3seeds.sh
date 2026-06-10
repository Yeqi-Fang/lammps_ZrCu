#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

NP="${NP:-12}"
LMP="${LMP:-lmp}"
CONDA_ENV="${CONDA_ENV:-lammps}"
USE_CONDA="${USE_CONDA:-1}"
DRY_RUN="${DRY_RUN:-0}"
RESUME="${RESUME:-1}"
START_SEED="${START_SEED:-1}"
END_SEED="${END_SEED:-3}"
INPUT="${INPUT:-ZrCu_N10000_slow_template.lammps.eam}"

TAGS=(
  N10000_seed1_q1e12
  N10000_seed2_q1e12
  N10000_seed3_q1e12
)
SEEDS=(
  246813
  357924
  468135
)

if [[ "$USE_CONDA" != "0" ]]; then
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
  conda activate "$CONDA_ENV"
fi

if ! command -v mpirun >/dev/null 2>&1; then
  echo "mpirun was not found."
  exit 127
fi
if ! command -v "$LMP" >/dev/null 2>&1; then
  echo "LAMMPS executable '$LMP' was not found in PATH."
  exit 127
fi

export OMP_NUM_THREADS=1

for i in "${!TAGS[@]}"; do
  seed_index=$((i + 1))
  if (( seed_index < START_SEED || seed_index > END_SEED )); then
    continue
  fi

  tag="${TAGS[$i]}"
  seed="${SEEDS[$i]}"
  final_sample="samples/Glass_Cu50Zr50_${tag}_0K_minimized.dat"
  out="run_ZrCu_${tag}.out"

  if [[ "$RESUME" == "1" && -s "$final_sample" ]]; then
    echo "Skipping ${tag}: ${final_sample} already exists."
    continue
  fi

  echo "============================================================"
  echo "Running ${tag}, seed=${seed}, NP=${NP}"
  echo "Slow quench: 1e12 K/s, quench_steps=1700000"
  echo "Output log: ${out}"
  echo "============================================================"
  echo "Command: mpirun -np ${NP} ${LMP} -in ${INPUT} -var run_tag ${tag} -var seed ${seed}"

  if [[ "$DRY_RUN" == "1" ]]; then
    continue
  fi

  mpirun -np "${NP}" "$LMP" -in "$INPUT" -var run_tag "$tag" -var seed "$seed" | tee "$out"
done
