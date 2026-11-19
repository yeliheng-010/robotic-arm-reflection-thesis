#!/bin/bash
#SBATCH --job-name=qualified-natural-review
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_data_review_v1/review-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/natural_qualified_pilot_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/qualified_data_review_v1:/home/yeliheng/grasp_server/ai_multimodal_requests_v1:/home/yeliheng/grasp_server/ai_tracking_facts_v1:/home/yeliheng/grasp_server/ai_observable_facts_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/qualified_data_review_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B review.py
