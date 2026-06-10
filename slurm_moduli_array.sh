#!/bin/bash
# SLURM array job: 0K AQS elastic moduli for 3 slow-quench seeds (q1e12).
# Runs relax + 28 strain LAMMPS jobs + fit_moduli.py per seed.
# Submit from ~/WORK/lammps_ZrCu/:
#   sbatch slurm_moduli_array.sh
#
# To run for 0.1 K/ps seeds instead:
#   sbatch --export=RATE_TAG=q1e11 slurm_moduli_array.sh
#SBATCH -J ZrCu_moduli
#SBATCH --array=1-3
#SBATCH -p cnall
#SBATCH -N 1
#SBATCH --ntasks-per-node=56
#SBATCH -o stdout.moduli.%A_%a
#SBATCH -e stderr.moduli.%A_%a
#SBATCH --no-requeue

cd "$SLURM_SUBMIT_DIR"

RATE_TAG="${RATE_TAG:-q1e12}"   # default: q1e12; override with --export

TAGS=(dummy "N10000_seed1_${RATE_TAG}" "N10000_seed2_${RATE_TAG}" "N10000_seed3_${RATE_TAG}")
TAG="${TAGS[$SLURM_ARRAY_TASK_ID]}"
OUTDIR="analysis_${TAG}/moduli"
FINAL_DAT="samples/Glass_Cu50Zr50_${TAG}_0K_minimized.dat"

echo "Task ${SLURM_ARRAY_TASK_ID}: moduli for ${TAG}  node=$(hostname)"

if [[ ! -s "$FINAL_DAT" ]]; then
  echo "ERROR: ${FINAL_DAT} missing — run simulation first." && exit 1
fi
if [[ -s "${OUTDIR}/moduli_summary.csv" ]]; then
  echo "SKIP: ${OUTDIR}/moduli_summary.csv already exists." && exit 0
fi

mkdir -p "$OUTDIR"

module load compilers/intel/oneapi-2023/config
module load soft/lammps/lammps-22Dec2022

echo "--- Zero-pressure relax ---"
mpirun -np 56 lmp_oneapi \
  -in relax_zeroP_0k_tagged.lmp \
  -var run_tag "${TAG}" \
  -screen none \
  -log "${OUTDIR}/relax_zeroP_0k.log"

# Initialize stress data files
cat > "${OUTDIR}/shear_xy_stress.dat" <<'HEADER'
# gamma tau_GPa pxy_GPa pe_per_atom_eV vol_A3 xy_A
HEADER
cat > "${OUTDIR}/shear_xz_stress.dat" <<'HEADER'
# gamma tau_GPa pxz_GPa pe_per_atom_eV vol_A3 xz_A
HEADER
cat > "${OUTDIR}/shear_yz_stress.dat" <<'HEADER'
# gamma tau_GPa pyz_GPa pe_per_atom_eV vol_A3 yz_A
HEADER
cat > "${OUTDIR}/bulk_stress.dat" <<'HEADER'
# eta hydro_GPa press_GPa pe_per_atom_eV vol_A3 density_g_cm3
HEADER

for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
  echo "  xy strain ${strain}"
  mpirun -np 56 lmp_oneapi -in modulus_shear_xy_0k_tagged.lmp \
    -var run_tag "${TAG}" -var strain "${strain}" \
    -screen none -log "${OUTDIR}/shear_xy_${strain}.log"
done
for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
  echo "  xz strain ${strain}"
  mpirun -np 56 lmp_oneapi -in modulus_shear_xz_0k_tagged.lmp \
    -var run_tag "${TAG}" -var strain "${strain}" \
    -screen none -log "${OUTDIR}/shear_xz_${strain}.log"
done
for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
  echo "  yz strain ${strain}"
  mpirun -np 56 lmp_oneapi -in modulus_shear_yz_0k_tagged.lmp \
    -var run_tag "${TAG}" -var strain "${strain}" \
    -screen none -log "${OUTDIR}/shear_yz_${strain}.log"
done
for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
  echo "  bulk strain ${strain}"
  mpirun -np 56 lmp_oneapi -in modulus_bulk_0k_tagged.lmp \
    -var run_tag "${TAG}" -var strain "${strain}" \
    -screen none -log "${OUTDIR}/bulk_${strain}.log"
done

echo "--- Fitting moduli ---"
CONDA_DIR="$HOME/WORK/fyq/miniconda3"
source "${CONDA_DIR}/etc/profile.d/conda.sh"
conda activate ovito
python fit_moduli.py --out "${OUTDIR}"

echo "DONE: ${TAG}  $(date)"
