#!/bin/bash
#SBATCH --job-name=visual-finetune-controlled
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_finetune_v1/train-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_training_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_finetune_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B smoke.py update
/home/yeliheng/grasp_server/qwen35/env/bin/python -B smoke.py reload
/home/yeliheng/grasp_server/qwen35/env/bin/python -B train.py
