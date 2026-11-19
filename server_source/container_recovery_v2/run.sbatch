#!/bin/bash
#SBATCH --job-name=layout-recover-sim
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=03:00:00
#SBATCH --output=/home/yeliheng/grasp_server/container_recovery_v2/run-%A_%a.log
#SBATCH --gres=gpu:1
#SBATCH --array=0-2%3
set -euo pipefail
source /home/yeliheng/grasp_server/container_recovery_v2/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/container_recovery_v2/run.py "$1" --shard "$SLURM_ARRAY_TASK_ID"
