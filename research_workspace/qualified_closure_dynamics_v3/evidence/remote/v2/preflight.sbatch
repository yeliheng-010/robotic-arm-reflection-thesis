#!/bin/bash
#SBATCH --job-name=closure-real-imports
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --no-requeue
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_dynamics_v2/preflight-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m qualified_closure_dynamics_v2.preflight
