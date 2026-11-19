#!/bin/bash
#SBATCH --job-name=visual-natural-data-review
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_data_review_v1/review-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_safe_visual_loop_v1/environment_v4.sh
export PYTHONPATH=/home/yeliheng/grasp_server/visual_data_review_v1:/home/yeliheng/grasp_server/qualified_data_review_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/visual_data_review_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B review.py
