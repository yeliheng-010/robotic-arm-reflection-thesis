#!/bin/bash
#SBATCH --job-name=closure-code-verify
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_dynamics_v1/verify-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m qualified_closure_dynamics_v1.test_runner
$SIM_PY -B -m qualified_closure_dynamics_v1.prepare
