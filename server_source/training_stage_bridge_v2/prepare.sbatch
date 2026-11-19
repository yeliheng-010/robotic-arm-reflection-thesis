#!/bin/bash
#SBATCH --job-name=training-bridge-code-freeze
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/training_stage_bridge_v2/prepare-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/training_stage_bridge_v2
/home/yeliheng/grasp_server/env_sim/bin/python -B prepare.py
