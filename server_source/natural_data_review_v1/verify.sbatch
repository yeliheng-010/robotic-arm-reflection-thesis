#!/bin/bash
#SBATCH --job-name=natural-data-review
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/natural_data_review_v1/review-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_natural_loop_v1/environment.sh
cd /home/yeliheng/grasp_server/natural_data_review_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_inventory -v
/home/yeliheng/grasp_server/env_sim/bin/python -B inventory.py /home/yeliheng/grasp_server/ai_natural_loop_v1 /home/yeliheng/grasp_server/natural_data_review_v1/inventory.json
