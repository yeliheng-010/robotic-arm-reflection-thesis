#!/bin/bash
#SBATCH --job-name=recovery-audited-progress
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_dataset_v1/progress-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_dataset_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B progress.py
