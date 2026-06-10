#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate lammps

export OMP_NUM_THREADS=1

mkdir -p analysis/moduli

cat > analysis/moduli/shear_xy_stress.dat <<'EOF'
# gamma tau_GPa pxy_GPa pe_per_atom_eV vol_A3 xy_A
EOF
cat > analysis/moduli/shear_xz_stress.dat <<'EOF'
# gamma tau_GPa pxz_GPa pe_per_atom_eV vol_A3 xz_A
EOF
cat > analysis/moduli/shear_yz_stress.dat <<'EOF'
# gamma tau_GPa pyz_GPa pe_per_atom_eV vol_A3 yz_A
EOF

cat > analysis/moduli/bulk_stress.dat <<'EOF'
# eta hydro_GPa press_GPa pe_per_atom_eV vol_A3 density_g_cm3
EOF

for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
  echo "shear strain ${strain}"
  mpirun -np 8 lmp -screen none -in modulus_shear_xy_0k.lmp -var strain "${strain}" -log "analysis/moduli/shear_${strain}.log"
done

for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
  echo "xz shear strain ${strain}"
  mpirun -np 8 lmp -screen none -in modulus_shear_xz_0k.lmp -var strain "${strain}" -log "analysis/moduli/shear_xz_${strain}.log"
done

for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
  echo "yz shear strain ${strain}"
  mpirun -np 8 lmp -screen none -in modulus_shear_yz_0k.lmp -var strain "${strain}" -log "analysis/moduli/shear_yz_${strain}.log"
done

for strain in -0.006 -0.004 -0.002 0.000 0.002 0.004 0.006; do
  echo "bulk strain ${strain}"
  mpirun -np 8 lmp -screen none -in modulus_bulk_0k.lmp -var strain "${strain}" -log "analysis/moduli/bulk_${strain}.log"
done

conda activate ovito
python fit_moduli.py
