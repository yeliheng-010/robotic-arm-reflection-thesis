#!/bin/bash
#SBATCH --job-name=recovery-export-audited
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_dataset_v1/export-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_dataset_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_export -v
/home/yeliheng/grasp_server/env_sim/bin/python -B export.py
