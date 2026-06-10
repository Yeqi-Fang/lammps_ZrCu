#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate lammps

export OMP_NUM_THREADS=1

mkdir -p logs

for np in 4 6 8 10 12 16 24; do
  flags=()
  if (( np > 12 )); then
    flags+=(--use-hwthread-cpus)
  fi

  out="logs/bench_np${np}.out"
  log="logs/bench_np${np}.log"

  echo "=== NP=${np} flags=${flags[*]-} ==="
  mpirun "${flags[@]}" -np "$np" lmp -in ZrCu_bench.lammps.eam -log "$log" > "$out" 2>&1

  grep -E "Performance:|Loop time of|BENCHMARK_FINISHED" "$out" | tail -n 4
done
