#!/bin/bash
#SBATCH --job-name=scene-control-first
#SBATCH --partition=batch
#SBATCH --gres=gpu:v100:1
#SBATCH --array=0-1%2
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/scene_qualification_v1/job-%A_%a.log
set -euo pipefail
source training/server/qwen35_env.sh
source /home/yeliheng/grasp_server/refinement_v3/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/scene_qualification_v1/run.py --shard "$SLURM_ARRAY_TASK_ID"
