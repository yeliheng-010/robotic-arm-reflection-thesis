#!/bin/bash
#SBATCH --job-name=visual-data-accounting-tests
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_data_review_v1/verify-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_safe_visual_loop_v1/environment_v4.sh
export PYTHONPATH=/home/yeliheng/grasp_server/visual_data_review_v1:/home/yeliheng/grasp_server/qualified_data_review_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/visual_data_review_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest discover -v
