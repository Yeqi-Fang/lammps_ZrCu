#!/usr/bin/env bash
# ============================================================
# Cluster environment setup — run ONCE on the login node cln01
# which has internet access.
# Usage:
#   ssh cln01
#   bash ~/WORK/lammps_ZrCu/setup_cluster.sh
# ============================================================
set -euo pipefail

WORKDIR="$HOME/WORK"
CONDA_DIR="$WORKDIR/miniconda3"
MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple/"

echo "=== Step 1: Install Miniconda into $CONDA_DIR ==="
if [[ ! -f "$CONDA_DIR/bin/conda" ]]; then
  INSTALLER="/apps/soft/anaconda3/Miniconda3-latest-Linux-x86_64.sh"
  if [[ ! -f "$INSTALLER" ]]; then
    echo "ERROR: Miniconda installer not found at $INSTALLER"
    echo "Download manually: wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    exit 1
  fi
  bash "$INSTALLER" -b -p "$CONDA_DIR"
  echo "Miniconda installed at $CONDA_DIR"
else
  echo "Miniconda already installed, skipping."
fi

source "$CONDA_DIR/etc/profile.d/conda.sh"

echo "=== Step 2: Create 'ovito' conda environment ==="
if conda env list | grep -q "^ovito "; then
  echo "'ovito' env already exists, skipping creation."
else
  conda create -n ovito python=3.10 -y
fi

conda activate ovito

echo "=== Step 3: Install Python packages (Tsinghua mirror) ==="
pip install --upgrade pip -i "$MIRROR"
pip install ovito numpy matplotlib pandas -i "$MIRROR"

echo "=== Step 4: Verify OVITO import ==="
python -c "import ovito; print('ovito', ovito.__version__, 'OK')"
python -c "import numpy, matplotlib, pandas; print('numpy/matplotlib/pandas OK')"

echo ""
echo "=== Setup complete! ==="
echo "Conda path: $CONDA_DIR"
echo "Activate with: source $CONDA_DIR/etc/profile.d/conda.sh && conda activate ovito"
echo ""
echo "Add to ~/.bashrc to make permanent:"
echo "  echo 'source $CONDA_DIR/etc/profile.d/conda.sh' >> ~/.bashrc"
