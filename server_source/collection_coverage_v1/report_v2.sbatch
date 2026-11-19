#!/bin/bash
#SBATCH --job-name=collection-selected-coverage-v2
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/collection_coverage_v1/report-v2-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/collection_coverage_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B report_v2.py
