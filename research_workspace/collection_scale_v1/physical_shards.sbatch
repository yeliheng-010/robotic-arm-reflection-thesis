#!/bin/bash
#SBATCH --job-name=recovery-physics-shard
#SBATCH --partition=batch
#SBATCH --array=0-3%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/collection_scale_v1/physical-shard-%A-%a.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/collection_scale_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B sc_physics.py shard
