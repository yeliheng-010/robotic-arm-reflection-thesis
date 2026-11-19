#!/bin/bash
#SBATCH --job-name=legal-goal-third
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:30:00
#SBATCH --gres=gpu:1
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_route_v3/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_route_v3/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_route_v3
$SIM_PY -B goal_worker.py
