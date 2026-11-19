#!/bin/bash
#SBATCH --job-name=targeted-data-review
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/targeted_data_review_v1/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/targeted_collection_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/targeted_data_review_v1:$PYTHONPATH
/home/yeliheng/grasp_server/env_sim/bin/python -m unittest discover -s /home/yeliheng/grasp_server/targeted_data_review_v1 -p 'test_*.py'
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/targeted_data_review_v1/build.py
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/targeted_data_review_v1/validate.py
