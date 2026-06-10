#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export INPUT="${INPUT:-ZrCu_N10000.lammps.eam}"
export OUT="${OUT:-run_ZrCu_N10000.out}"
export NP="${NP:-8}"

exec ./run_zrcu_local.sh
