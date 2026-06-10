#!/usr/bin/env bash
# Submit all 6 simulation jobs to the cluster:
#   - 0.01 K/ps  (10^10 K/s)  × 3 seeds  [~61 h/seed, 3 nodes in parallel]
#   - 0.1  K/ps  (10^11 K/s)  × 3 seeds  [~ 6 h/seed, 3 nodes in parallel]
#
# Run from ~/WORK/lammps_ZrCu/:
#   bash submit_all_slurm.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "Submitting 0.01 K/ps array (q1e10, 3 seeds)..."
JID1=$(sbatch --parsable slurm_001kps_array.sh)
echo "  Job ID: ${JID1}"

echo "Submitting 0.1 K/ps array (q1e11, 3 seeds)..."
JID2=$(sbatch --parsable slurm_01kps_array.sh)
echo "  Job ID: ${JID2}"

echo ""
echo "All 6 jobs submitted."
echo "Monitor with:  squeue -u \$USER"
echo ""
echo "After 0.1 K/ps jobs finish (~6h), run analysis:"
echo "  sbatch --export=RATE_TAG=q1e11,OUT_DIR=analysis_N10000_01kps_3seeds,QUENCH_STEPS=17000000 slurm_analysis.sh"
echo ""
echo "After 0.01 K/ps jobs finish (~61h), run analysis:"
echo "  sbatch --export=RATE_TAG=q1e10,OUT_DIR=analysis_N10000_001kps_3seeds,QUENCH_STEPS=170000000 slurm_analysis.sh"
