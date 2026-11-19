#!/bin/bash
#SBATCH --job-name=qualified-task-audit
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_task_v1/audit-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 260 $SIM_PY -B -m qualified_task_v1.audit
