#!/bin/bash
#SBATCH --job-name=candidate-loop-sim
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --array=0-2%3
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=03:00:00
#SBATCH --output=/home/yeliheng/grasp_server/set_closed_loop_v1/physical-%A_%a.log
set -euo pipefail
source /home/yeliheng/grasp_server/set_closed_loop_v1/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/set_closed_loop_v1/run.py "$1" --shard "$SLURM_ARRAY_TASK_ID"
