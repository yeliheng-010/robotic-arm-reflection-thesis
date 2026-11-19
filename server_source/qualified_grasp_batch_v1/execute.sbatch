#!/bin/bash
#SBATCH --job-name=grasp-batch-200
#SBATCH --partition=batch
#SBATCH --array=0-199%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:12:00
#SBATCH --no-requeue
#SBATCH --output=/home/yeliheng/grasp_server/qualified_grasp_batch_v1/execute-%A_%a.log
set -euo pipefail
cd /home/yeliheng/grasp_server
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
exec $SIM_PY -B -m qualified_grasp_batch_v1.worker
