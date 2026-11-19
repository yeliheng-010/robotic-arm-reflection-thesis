#!/bin/bash
#SBATCH --job-name=qualified-exec-preflight_audit
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:12:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_execution_v1/preflight_audit-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m qualified_execution_v1.preflight audit
