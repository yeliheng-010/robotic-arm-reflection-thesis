#!/bin/bash
#SBATCH --job-name=collection-coverage-equivalence
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/collection_coverage_v1/verify-v2-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/collection_coverage_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B verify_v2.py
