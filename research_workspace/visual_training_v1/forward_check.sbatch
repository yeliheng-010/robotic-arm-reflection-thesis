#!/bin/bash
#SBATCH --job-name=visual-training-forward-only
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_training_v1/forward-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_training_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_training_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B forward_check.py
