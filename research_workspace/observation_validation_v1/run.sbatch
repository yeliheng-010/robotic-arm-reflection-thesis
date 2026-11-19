#!/bin/bash
#SBATCH --job-name=mechanism-pilot
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --array=0-3%4
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/home/yeliheng/grasp_server/observation_validation_v1/run-%A_%a.log
set -euo pipefail
source /home/yeliheng/grasp_server/observation_validation_v1/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/observation_validation_v1/run.py "$1" --shard "$SLURM_ARRAY_TASK_ID"
