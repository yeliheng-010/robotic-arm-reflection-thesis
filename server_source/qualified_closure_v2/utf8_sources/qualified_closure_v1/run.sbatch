#!/bin/bash
#SBATCH --job-name=closure-preflight
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_v1/run-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m unittest qualified_closure_v1.test_policy qualified_closure_v1.test_adapter qualified_execution_v1.test_policy qualified_execution_v1.test_guards qualified_entry_v1.test_commands -v
$SIM_PY -B -m qualified_closure_v1.worker
