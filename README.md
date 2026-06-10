# CuZr metallic-glass preparation and AQS simulations

This repository contains LAMMPS input scripts and job-submission scripts to generate binary Cu-Zr amorphous-glass configurations and then perform athermal quasistatic shear (AQS) simulations. The workflow is organized in four main stages:

1. Create an equilibrated high-temperature liquid.
2. Quench the liquid to obtain independent glass configurations.
3. Relax each glass at low temperature and fix the final volume using an NPT-to-NVT procedure.
4. Perform AQS shear simulations and extract avalanche-related quantities.

The current setup is written for a Zr\(_{50}\)Cu\(_{50}\) binary alloy using an EAM/alloy potential.

---

## Repository structure

```text
.
├── initial.lmp          # Generate equilibrated liquid configurations
├── quenching.lmp        # Quench the liquid and generate glass samples
├── loop_nvt.lmp         # NPT volume relaxation followed by NVT equilibration
├── run_nvt_loop.bash    # PBS script to run NVT equilibration for all glasses
├── AQS.lmp              # AQS shear simulation input script
├── run_aqs.bash         # PBS script to run AQS over all NVT-final configurations
├── potentials/          # Interatomic potentials
├── NpT_samples/         # Output liquid configurations
├── samples/             # Output quenched glass configurations
├── fix_vol/             # Output NVT-final fixed-volume glass configurations
└── Avalanches/          # Output AQS avalanche data
```

> **Note:** the run scripts may need small edits depending on the cluster, queue system, LAMMPS executable path, and module environment.

---

## Requirements

- LAMMPS compiled with MPI support.
- Access to the `eam/alloy` pair style.
- The Cu-Zr EAM potential file:

```text
potentials/ZrCuAl.lammps.eam
```

- A PBS-compatible cluster environment for the provided `.bash` scripts, or equivalent SLURM scripts if running on another cluster.

The scripts currently use paths such as:

```bash
/home/des01/aantone/ralvarez/mylammps/src/lmp_mpi
```

You should replace this path with the location of your own LAMMPS executable if needed.

---

## Workflow overview

### Step 1: Generate the initial liquid

The file `initial.lmp` creates random Zr and Cu atoms in a periodic simulation box and equilibrates the system at high temperature using an NPT ensemble. The current composition is Zr\(_{50}\)Cu\(_{50}\), with atom types:

```text
type 1 = Zr
type 2 = Cu
```

The script currently loops over several system sizes:

```lammps
variable atom_counts index 100000 50000 20000 8000
```

For each size, it equilibrates the liquid at:

```text
T = 2000 K
P = 0 bar
```

and writes the equilibrated liquid configurations to:

```text
NpT_samples/Liquid_N_<N>.dat
```

Example output:

```text
NpT_samples/Liquid_N_100000.dat
```

Run example:

```bash
mpirun -np 120 /path/to/lmp_mpi -in initial.lmp -var RANDOM ${RANDOM}
```

---

### Step 2: Quench the liquid to obtain glass configurations

The file `quenching.lmp` reads the equilibrated liquid from `NpT_samples/` and performs a quench from 2000 K to 0.01 K using an NPT ensemble.

The current script is set to generate 20 independent glass samples:

```lammps
variable sample_id loop 20
```

The current system size is:

```lammps
variable atom_sizes index 100000
```

For each sample, a different random seed is used to assign velocities before quenching. The quenched configurations are written to:

```text
samples/Glass_N_<N>_s<sample_id>.dat
```

Example outputs:

```text
samples/Glass_N_100000_s1.dat
samples/Glass_N_100000_s2.dat
...
samples/Glass_N_100000_s20.dat
```

Run example:

```bash
mpirun -np 120 /path/to/lmp_mpi -in quenching.lmp -var RANDOM ${RANDOM}
```

---

### Step 3: NPT-to-NVT fixed-volume preparation

After quenching, each glass is further equilibrated at low temperature using `loop_nvt.lmp`.

This step has two parts:

1. **NPT relaxation** at low temperature to estimate the average box dimensions.
2. **NVT equilibration** after resizing the box to the averaged dimensions.

The script reads restart files from:

```text
samples/<fname>.dat
```

and writes the final fixed-volume configurations to:

```text
fix_vol/<fname>_NVT_final.dat
```

Example output:

```text
fix_vol/Glass_N_100000_s1_NVT_final.dat
```

The script `run_nvt_loop.bash` loops automatically over all files matching:

```bash
samples/Glass_N_*.dat
```

and passes each filename to LAMMPS through the variable `fname`:

```bash
mpirun -n 120 /path/to/lmp_mpi -in loop_nvt.lmp -v fname "$base" -v RANDOM ${RANDOM}
```

Submit example:

```bash
qsub run_nvt_loop.bash
```

---

### Step 4: AQS shear simulations

The file `AQS.lmp` performs athermal quasistatic shear on each fixed-volume glass configuration.

The simulation uses the following basic AQS cycle:

1. Store the current energy and stress.
2. Apply a small affine shear strain increment.
3. Minimize the energy using FIRE.
4. Record stress, strain, energy drop, and avalanche-related quantities.
5. Repeat until the target total strain is reached.

The current shear increment is:

```lammps
variable epsilon equal 1e-4
```

The current total number of AQS steps is:

```lammps
variable total_steps equal 4000
```

This corresponds to a total shear deformation of approximately:

```text
4000 × 1e-4 = 0.40
```

or 40% shear strain.

The AQS script writes avalanche data to:

```text
Avalanches/avalanches_<fname>.dat
```

The output columns are:

```text
strain_xy stress_gpa dE_Umut dE_Paper d_sigma
```

where:

- `strain_xy` is the accumulated shear strain.
- `stress_gpa` is the shear stress in GPa.
- `dE_Umut` is the energy drop after minimization, normalized by the number of atoms.
- `dE_Paper` is an alternative energy-drop definition including the elastic work term.
- `d_sigma` is the stress-drop-related quantity corrected by the elastic loading contribution.

Submit example:

```bash
qsub run_aqs.bash
```

---

## Restart logic for AQS

The `run_aqs.bash` script includes a simple restart mechanism. For each sample, it checks whether a progress file exists:

```text
current_step_<FNAME>.txt
```

If the file exists, the script reads the last completed step and resumes from:

```text
START_STEP = LAST_STEP + 1
```

The value of `START_STEP` is passed to LAMMPS using:

```bash
-var START_STEP "$START_STEP"
```

At the end of a successful AQS run, the LAMMPS script prints:

```text
SIMULATION_FINISHED_SUCCESSFULLY
```

The Bash script checks for this message in the sample-specific log file. If the message is found, the progress file is removed; otherwise, the script exits and asks the user to inspect the corresponding log file.

---

## Important notes before running


### 1. Check relative paths

`AQS.lmp` reads configurations from:

```lammps
read_data ../fix_vol/${fname}.dat
```

while the run script loops over:

```bash
../fix_vol/Glass_N_2*_NVT_final.dat
```

This means `run_aqs.bash` is expected to be launched from a directory where `../fix_vol/` exists. If your directory structure is different, update the path accordingly.

### 2. Create output directories

Before running the full workflow, make sure the required directories exist:

```bash
mkdir -p potentials NpT_samples samples fix_vol Avalanches Dumps Restarts
```

### 3. Cluster-specific settings

The provided run scripts are written for a PBS environment and load the following modules:

```bash
module load gnu/5.4.0
module load intel/2015
module load impi/5.1
```

If you run on a different cluster, update:

- queue or partition name,
- number of nodes and MPI tasks,
- module names,
- LAMMPS executable path,
- MPI launcher (`mpirun`, `srun`, etc.).

---

## Suggested execution order

```bash
# 1. Generate equilibrated liquid
mpirun -np 120 /path/to/lmp_mpi -in initial.lmp -var RANDOM ${RANDOM}

# 2. Generate 20 quenched glass configurations
mpirun -np 120 /path/to/lmp_mpi -in quenching.lmp -var RANDOM ${RANDOM}

# 3. Run NVT preparation for all glasses
qsub run_nvt_loop.bash

# 4. Run AQS simulations for all fixed-volume glasses
qsub run_aqs.bash
```

---

## Expected output files

After the full workflow, the main outputs should be:

```text
NpT_samples/Liquid_N_100000.dat
samples/Glass_N_100000_s1.dat
...
samples/Glass_N_100000_s20.dat
fix_vol/Glass_N_100000_s1_NVT_final.dat
...
fix_vol/Glass_N_100000_s20_NVT_final.dat
Avalanches/avalanches_Glass_N_100000_s1_NVT_final.dat
...
Avalanches/avalanches_Glass_N_100000_s20_NVT_final.dat
```

---

## Citation / acknowledgement

If you use or modify this workflow, please acknowledge the original repository and cite the relevant interatomic potential and simulation methodology used for the Cu-Zr metallic-glass system.
