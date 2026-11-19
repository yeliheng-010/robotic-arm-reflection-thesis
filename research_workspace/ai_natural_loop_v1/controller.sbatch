#!/bin/bash
#SBATCH --job-name=natural-loop-eight
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_natural_loop_v1/controller-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_natural_loop_v1/environment.sh
cd /home/yeliheng/grasp_server/ai_natural_loop_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B nc_controller.py
