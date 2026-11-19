#!/bin/bash
#SBATCH --job-name=recovery-physics-integrity-v3
#SBATCH --partition=batch
#SBATCH --array=0-3%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_integrity_v3/physical-shard-%A-%a.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_integrity_v3
/home/yeliheng/grasp_server/env_sim/bin/python -B iv3_jobs.py shard
