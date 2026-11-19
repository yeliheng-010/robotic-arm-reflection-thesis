#!/bin/bash
#SBATCH --job-name=visual-final-checkpoint-reload
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_checkpoint_review_v1/review-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_training_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_checkpoint_review_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B review.py
