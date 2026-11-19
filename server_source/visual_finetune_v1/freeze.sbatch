#!/bin/bash
#SBATCH --job-name=visual-finetune-gate-freeze
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_finetune_v1/freeze-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_training_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_finetune_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B freeze.py
