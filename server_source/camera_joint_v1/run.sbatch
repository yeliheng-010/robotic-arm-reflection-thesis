#!/bin/bash
#SBATCH --job-name=camera_joint_v1-run
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:08:00
#SBATCH --output=/home/yeliheng/grasp_server/camera_joint_v1/run-%A_%a.log
#SBATCH --gres=gpu:1
#SBATCH --array=0-11%2
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 450 $SIM_PY -B -m camera_joint_v1.worker
