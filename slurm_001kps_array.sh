#!/bin/bash
# SLURM array job: Cu50Zr50 N=10000, quench at 0.01 K/ps (10^10 K/s), 3 seeds in parallel.
# Expected wall time: ~61 h per seed with 56 cores.
# Submit from ~/WORK/lammps_ZrCu/:
#   sbatch slurm_001kps_array.sh
#SBATCH -J ZrCu_001kps
#SBATCH --array=1-3
#SBATCH -p cnall
#SBATCH -N 1
#SBATCH --ntasks-per-node=56
#SBATCH -o stdout.001kps.%A_%a
#SBATCH -e stderr.001kps.%A_%a
#SBATCH --no-requeue

cd "$SLURM_SUBMIT_DIR"
mkdir -p logs dumps restarts samples observables

# quench_steps = round((2000-300) / 0.01 / 0.001) = 170,000,000
QUENCH_STEPS=170000000

TAGS=(dummy N10000_seed1_q1e10 N10000_seed2_q1e10 N10000_seed3_q1e10)
SEEDS=(0     246813             357924             468135)

TAG="${TAGS[$SLURM_ARRAY_TASK_ID]}"
SEED="${SEEDS[$SLURM_ARRAY_TASK_ID]}"
FINAL="samples/Glass_Cu50Zr50_${TAG}_0K_minimized.dat"

echo "Task ${SLURM_ARRAY_TASK_ID}: ${TAG}  seed=${SEED}  quench_steps=${QUENCH_STEPS}  node=$(hostname)"

if [[ -s "$FINAL" ]]; then
  echo "SKIP: ${FINAL} already exists."
  exit 0
fi

module load compilers/intel/oneapi-2023/config
module load soft/lammps/lammps-22Dec2022

mpirun -np $SLURM_NTASKS lmp_oneapi \
  -in  ZrCu_N10000_quench_template.lammps.eam \
  -var run_tag      "${TAG}" \
  -var seed         "${SEED}" \
  -var quench_steps "${QUENCH_STEPS}" \
  -screen none

echo "DONE: ${TAG}  $(date)"
