#!/bin/bash
#PBS -N BMG_test
### Arquivos de saida
#PBS -e test.err
#PBS -o test.out

### Definindo a fila e o número de processadores
## no caso, estamos solicitando para rodar na fila par12
## e solicitando 1 node e 12 cores em cada um, totalizando 12 cores
#PBS -q par120
#PBS -l nodes=3:ppn=40

cd $PBS_O_WORKDIR

module load gnu/5.4.0
module load intel/2015
module load impi/5.1



export I_MPI_HYDRA_BOOTSTRAP=rsh
export I_MPI_HYDRA_BOOTSTRAP_EXEC=/opt/pbs/bin/pbs_tmrsh
export I_MPI_DEVICE=rdssm
export I_MPI_FABRICS=ofa


# Loop through all files in the samples folder
for file in samples/Glass_N_*.dat; do
    # Extract just the name (e.g., Glass_N_8000_s1)
    base=$(basename "$file" .dat)
    
    echo "Starting sample: $base"
    
    # Run LAMMPS
    mpirun -n 120 /home/des01/aantone/ralvarez/mylammps/src/lmp_mpi -in loop_nvt.lmp -v fname "$base" -v RANDOM ${RANDOM}
    
    echo "Finished sample: $base"
done



