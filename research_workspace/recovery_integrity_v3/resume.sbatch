#!/bin/bash
#SBATCH --job-name=recovery-resume-unconsumed-v3
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_integrity_v3/resume-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
export RECOVERY_BATCH=6
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_integrity_v3
/home/yeliheng/grasp_server/env_sim/bin/python -B iv3_jobs.py resume
