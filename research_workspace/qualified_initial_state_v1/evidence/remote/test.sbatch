#!/bin/bash
#SBATCH --job-name=initial-json-tests
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --no-requeue
#SBATCH --output=/home/yeliheng/grasp_server/qualified_initial_state_v1/tests-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m unittest qualified_initial_state_v1.test_initial -v
