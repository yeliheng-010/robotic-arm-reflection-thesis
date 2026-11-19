#!/bin/bash
#SBATCH --job-name=visual-final-checkpoint-code-checks
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_checkpoint_review_v1/verify-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_training_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_checkpoint_review_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B -m unittest test_policy -v
/home/yeliheng/grasp_server/qwen35/env/bin/python -B verify.py
