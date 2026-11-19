#!/bin/bash
#SBATCH --job-name=full-grasp-once
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:12:00
#SBATCH --no-requeue
#SBATCH --output=/home/yeliheng/grasp_server/qualified_full_task_trial_v1/execute-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m qualified_full_task_trial_v1.worker
