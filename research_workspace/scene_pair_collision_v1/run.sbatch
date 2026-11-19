#!/bin/bash
#SBATCH --job-name=collision-run
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_collision_v1/run-%j.log
#SBATCH --gres=gpu:1
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_collision_v1/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_collision_v1
$SIM_PY cr_worker.py
