#!/bin/bash
#SBATCH --job-name=safe-visual-three-policies-v3
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_safe_visual_loop_v1/run-v3-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_safe_visual_loop_v1/environment_v3.sh
cd /home/yeliheng/grasp_server/ai_safe_visual_loop_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B prepare_v3.py
/home/yeliheng/grasp_server/env_sim/bin/python -B controller_v3.py
