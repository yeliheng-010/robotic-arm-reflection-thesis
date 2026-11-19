#!/bin/bash
#SBATCH --job-name=container-layout
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=06:00:00
#SBATCH --gres=gpu:1
#SBATCH --array=0-3%4
#SBATCH --output=/home/yeliheng/grasp_server/container_layout_v2/physics-%A_%a.log
set -euo pipefail
source /home/yeliheng/grasp_server/container_layout_v2/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/container_layout_v2/cl_run.py "$1" "$SLURM_ARRAY_TASK_ID"
