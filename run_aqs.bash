#!/bin/bash
#PBS -N aqs_2
### Arquivos de saida
#PBS -e test.err
#PBS -o test.out

### Definindo a fila e o número de processadores
## no caso, estamos solicitando para rodar na fila par12
## e solicitando 1 node e 12 cores em cada um, totalizando 12 cores
#PBS -q par120
#PBS -l nodes=3:ppn=40


cd $PBS_O_WORKDIR

# Load modules
module load gnu/5.4.0
module load intel/2015
module load impi/5.1

# MPI Environment setup
export I_MPI_HYDRA_BOOTSTRAP=rsh
export I_MPI_HYDRA_BOOTSTRAP_EXEC=/opt/pbs/bin/pbs_tmrsh
export I_MPI_DEVICE=rdssm
export I_MPI_FABRICS=ofa

# Ensure directories exist
mkdir -p Avalanches Dumps Restarts

# 1. We loop through all .dat files in the fix_vol directory
# 2. We extract the base name to use as 'fname' in LAMMPS
for FILEPATH in  ../fix_vol/Glass_N_2*_NVT_final.dat; do
    
    # Extract filename without path and without .dat
    # Result example: Glass_N_100000_s1_NVT_final
    FNAME=$(basename "$FILEPATH" .dat)
    
    # RESTART LOGIC: Unified to .txt
    PROGRESS_FILE="current_step_${FNAME}.txt"

    if [ -f "$PROGRESS_FILE" ]; then
        # FIXED: Changed .dat to .txt to match the check above
        LAST_STEP=$(cat "$PROGRESS_FILE")
        START_STEP=$((LAST_STEP + 1))
        echo "Resuming $FNAME from step $START_STEP"
    else
        START_STEP=1
        echo "Starting $FNAME from initial state"
    fi

    # Run LAMMPS
    # Output is piped to a unique log for each sample to avoid overwriting
    mpirun -n 120 /home/des01/aantone/ralvarez/mylammps/src/lmp_mpi \
           -in AQS.lmp \
           -var fname "$FNAME" \
           -var START_STEP "$START_STEP" > "log.${FNAME}"

    # Check specific log for success
    if grep -q "SIMULATION_FINISHED_SUCCESSFULLY" "log.${FNAME}"; then
        echo "Sample $FNAME completed successfully."
        rm -f "$PROGRESS_FILE"
    else
        echo "Sample $FNAME interrupted. Check log.${FNAME} for details."
        exit 1 
    fi
done
