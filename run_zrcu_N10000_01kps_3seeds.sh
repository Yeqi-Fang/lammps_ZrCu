#!/usr/bin/env bash
# Run Cu50Zr50 N=10000 quench at 0.1 K/ps (10^11 K/s) for 3 independent seeds.
# Tags: N10000_seed{1,2,3}_q1e11
# Expected wall time: ~28 hours per seed with NP=12.
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

NP="${NP:-12}"
RESUME="${RESUME:-1}"
START_SEED="${START_SEED:-1}"
END_SEED="${END_SEED:-3}"
export OMP_NUM_THREADS=1

# Quench rate and step count (shell computes to pass clean integer to LAMMPS)
QUENCH_RATE_KPS="0.1"   # K/ps = 10^11 K/s
T_MELT=2000; T_FINAL=300; DT="0.001"
QUENCH_STEPS=$(python3 -c "print(round((${T_MELT}-${T_FINAL})/${QUENCH_RATE_KPS}/${DT}))")
# = round(1700 / 0.1 / 0.001) = 17000000

echo "Quench rate: ${QUENCH_RATE_KPS} K/ps  =>  quench_steps = ${QUENCH_STEPS}"

TAGS=(
  N10000_seed1_q1e11
  N10000_seed2_q1e11
  N10000_seed3_q1e11
)
SEEDS=(246813 357924 468135)

for i in "${!TAGS[@]}"; do
  seed_index=$((i + 1))
  if (( seed_index < START_SEED || seed_index > END_SEED )); then
    continue
  fi

  tag="${TAGS[$i]}"
  seed="${SEEDS[$i]}"
  final_sample="samples/Glass_Cu50Zr50_${tag}_0K_minimized.dat"

  if [[ "$RESUME" == "1" && -s "$final_sample" ]]; then
    echo "Skipping ${tag}: ${final_sample} already exists."
    continue
  fi

  echo "=============================="
  echo "Running ${tag}  seed=${seed}  quench_steps=${QUENCH_STEPS}"
  echo "=============================="

  mpirun -np "${NP}" lmp \
    -in ZrCu_N10000_quench_template.lammps.eam \
    -var run_tag  "${tag}" \
    -var seed     "${seed}" \
    -var quench_steps "${QUENCH_STEPS}" \
    -screen none

  echo "Finished ${tag}"
done

echo "All requested seeds complete."
