#!/bin/bash
# SLURM array job: Cu50Zr50 N=10000, quench at 1 K/ps (10^12 K/s), 3 seeds in parallel.
# Submit from ~/WORK/lammps_ZrCu/:
#   sbatch slurm_1kps_array.sh
#
# To run only specific seeds: sbatch --array=2-3 slurm_1kps_array.sh
#SBATCH -J ZrCu_1kps
#SBATCH --array=1-3
#SBATCH -p cnall
#SBATCH -N 1
#SBATCH --ntasks-per-node=56
#SBATCH -o stdout.1kps.%A_%a
#SBATCH -e stderr.1kps.%A_%a
#SBATCH --no-requeue

WORKDIR="$HOME/WORK/lammps_ZrCu"
cd "$WORKDIR"
mkdir -p logs dumps restarts samples observables

# 1-indexed arrays (element 0 unused)
TAGS=(dummy N10000_seed1_q1e12 N10000_seed2_q1e12 N10000_seed3_q1e12)
SEEDS=(0     246813             357924             468135)

TAG="${TAGS[$SLURM_ARRAY_TASK_ID]}"
SEED="${SEEDS[$SLURM_ARRAY_TASK_ID]}"
FINAL="samples/Glass_Cu50Zr50_${TAG}_0K_minimized.dat"

echo "Task ${SLURM_ARRAY_TASK_ID}: ${TAG}  seed=${SEED}  node=$(hostname)"

if [[ -s "$FINAL" ]]; then
  echo "SKIP: ${FINAL} already exists."
  exit 0
fi

module load compilers/intel/oneapi-2023/config
module load soft/lammps/lammps-22Dec2022

mpirun -np 56 lmp_oneapi \
  -in  ZrCu_N10000_slow_template.lammps.eam \
  -var run_tag "${TAG}" \
  -var seed    "${SEED}" \
  -screen none

echo "DONE: ${TAG}  $(date)"
