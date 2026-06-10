#!/usr/bin/env bash
set -euo pipefail

NP="${NP:-8}"
LMP="${LMP:-lmp}"
INPUT="${INPUT:-ZrCu.lammps.eam}"
OUT="${OUT:-run_ZrCu.out}"
CONDA_ENV="${CONDA_ENV:-lammps}"
USE_CONDA="${USE_CONDA:-1}"
DRY_RUN="${DRY_RUN:-0}"
MPI_EXTRA_FLAGS="${MPI_EXTRA_FLAGS:-}"
USE_HWTHREADS="${USE_HWTHREADS:-0}"

cd "$(dirname "$0")"

if [[ "$USE_HWTHREADS" == "1" && "$MPI_EXTRA_FLAGS" != *"--use-hwthread-cpus"* ]]; then
  MPI_EXTRA_FLAGS="--use-hwthread-cpus ${MPI_EXTRA_FLAGS}"
fi

if [[ "$USE_CONDA" != "0" ]]; then
  if [[ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
  elif [[ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
  elif [[ -f "$HOME/miniforge3/etc/profile.d/conda.sh" ]]; then
    source "$HOME/miniforge3/etc/profile.d/conda.sh"
  elif [[ -f "$HOME/mambaforge/etc/profile.d/conda.sh" ]]; then
    source "$HOME/mambaforge/etc/profile.d/conda.sh"
  elif command -v conda >/dev/null 2>&1 && [[ "$(command -v conda)" != /mnt/c/* ]]; then
    eval "$(conda shell.bash hook)"
  else
    echo "Conda shell hook was not found. Activate manually first, or run USE_CONDA=0 ./run_zrcu_local.sh"
    exit 127
  fi

  echo "Activating conda environment: ${CONDA_ENV}"
  conda activate "$CONDA_ENV"
fi

if ! command -v "$LMP" >/dev/null 2>&1; then
  echo "LAMMPS executable '$LMP' was not found in PATH."
  echo "Check the conda environment, or run with LMP=/path/to/lmp_mpi ./run_zrcu_local.sh"
  exit 127
fi

if command -v mpirun >/dev/null 2>&1; then
  echo "Running: mpirun ${MPI_EXTRA_FLAGS} -np ${NP} ${LMP} -in ${INPUT}"
  if [[ "$DRY_RUN" == "1" ]]; then
    exit 0
  fi
  # shellcheck disable=SC2086
  mpirun ${MPI_EXTRA_FLAGS} -np "${NP}" "$LMP" -in "$INPUT" | tee "$OUT"
else
  echo "mpirun was not found; running single-process LAMMPS."
  echo "Running: ${LMP} -in ${INPUT}"
  if [[ "$DRY_RUN" == "1" ]]; then
    exit 0
  fi
  "$LMP" -in "$INPUT" | tee "$OUT"
fi
