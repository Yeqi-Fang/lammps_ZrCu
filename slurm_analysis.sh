#!/bin/bash
# SLURM job: Voronoi + convergence + aggregate analysis for a set of seeds.
# By default analyzes q1e12 (1 K/ps) seeds.
# Submit from ~/WORK/lammps_ZrCu/:
#   sbatch slurm_analysis.sh
#
# For 0.1 K/ps seeds:
#   sbatch --export=RATE_TAG=q1e11,OUT_DIR=analysis_N10000_01kps_3seeds,QUENCH_STEPS=17000000 slurm_analysis.sh
#SBATCH -J ZrCu_analysis
#SBATCH -p cnall
#SBATCH -N 1
#SBATCH --ntasks-per-node=4
#SBATCH -o stdout.analysis.%j
#SBATCH -e stderr.analysis.%j
#SBATCH --no-requeue

cd "$SLURM_SUBMIT_DIR"

RATE_TAG="${RATE_TAG:-q1e12}"
QUENCH_STEPS="${QUENCH_STEPS:-1700000}"
OUT_DIR="${OUT_DIR:-analysis_N10000_slow_3seeds}"

TAGS=(
  "N10000_seed1_${RATE_TAG}"
  "N10000_seed2_${RATE_TAG}"
  "N10000_seed3_${RATE_TAG}"
)

CONDA_DIR="$HOME/WORK/fyq/miniconda3"
source "${CONDA_DIR}/etc/profile.d/conda.sh"
conda activate ovito

echo "Analyzing ${RATE_TAG} seeds, quench_steps=${QUENCH_STEPS}"

for tag in "${TAGS[@]}"; do
  dump="dumps/Glass_Cu50Zr50_${tag}_300K_equilibrated.dump"
  if [[ ! -s "$dump" ]]; then
    echo "SKIP ${tag}: dump missing."
    continue
  fi
  echo "--- Analyzing ${tag} ---"
  python analyze_zrcu_structure_robust.py --tag "$tag"
  python check_convergence_thermo.py \
    --tag "$tag" \
    --melt-steps   100000 \
    --quench-steps "${QUENCH_STEPS}" \
    --eq-steps     100000
done

python aggregate_seed_analyses.py \
  --tags "${TAGS[@]}" \
  --out  "${OUT_DIR}"

echo "DONE  $(date)"
