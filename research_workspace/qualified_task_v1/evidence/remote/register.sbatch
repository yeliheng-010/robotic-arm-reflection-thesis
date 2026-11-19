#!/bin/bash
#SBATCH --job-name=qualified-task-register
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_task_v1/register-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m unittest qualified_task_v1.test_snapshot -v
$SIM_PY -B -m qualified_task_v1.register
