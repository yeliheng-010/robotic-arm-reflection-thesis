#!/bin/bash
#SBATCH --job-name=safe-visual-three-policies
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_safe_visual_loop_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_safe_visual_loop_v1/environment.sh
cd /home/yeliheng/grasp_server/ai_safe_visual_loop_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B prepare.py
/home/yeliheng/grasp_server/env_sim/bin/python -B controller.py
