#!/bin/bash
#SBATCH --job-name=visual-gradient-no-update
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_training_v1/gradient-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_training_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_training_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B gradient_check.py
