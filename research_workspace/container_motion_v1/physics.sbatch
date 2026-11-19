#!/bin/bash
#SBATCH --job-name=cm-physics
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=03:00:00
#SBATCH --gres=gpu:1
#SBATCH --array=0-3%4
#SBATCH --output=/home/yeliheng/grasp_server/container_motion_v1/physics-%A_%a.log
set -euo pipefail
source /home/yeliheng/grasp_server/container_motion_v1/environment.sh
cd /home/yeliheng/grasp_server/container_motion_v1
/home/yeliheng/grasp_server/env_sim/bin/python run.py "$1" --shard "$SLURM_ARRAY_TASK_ID"
