#!/bin/bash
#SBATCH --job-name=training-stage-gate-watch
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=24:00:00
#SBATCH --output=/home/yeliheng/grasp_server/training_stage_bridge_v2/watch-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/training_stage_bridge_v2
/home/yeliheng/grasp_server/env_sim/bin/python -B watch.py
