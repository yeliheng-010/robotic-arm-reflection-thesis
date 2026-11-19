#!/bin/bash
#SBATCH --job-name=qualified-task-initial-v2
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:06:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_task_v1/initial-v2-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m unittest qualified_task_v1.test_snapshot qualified_task_v1.test_stop -v
$SIM_PY -B -m qualified_task_v1.initial_v2 register
SLURM_ARRAY_TASK_ID=0 timeout 140 $SIM_PY -B -m qualified_task_v1.initial_v2 run
SLURM_ARRAY_TASK_ID=1 timeout 140 $SIM_PY -B -m qualified_task_v1.initial_v2 run
