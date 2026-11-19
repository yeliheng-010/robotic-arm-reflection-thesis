#!/bin/bash
#SBATCH --job-name=pose-fresh-scenes
#SBATCH --partition=batch
#SBATCH --array=0-11%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:08:00
#SBATCH --output=/home/yeliheng/grasp_server/pose_fresh_v1/scene-%A_%a.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 450 $SIM_PY -B -m pose_fresh_v1.worker
