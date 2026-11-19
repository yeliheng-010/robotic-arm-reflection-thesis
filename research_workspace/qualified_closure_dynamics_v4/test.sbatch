#!/bin/bash
#SBATCH --job-name=closure-v4-tests
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --no-requeue
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_dynamics_v4/tests-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m unittest qualified_closure_dynamics_v4.test_gpu_entry -v
