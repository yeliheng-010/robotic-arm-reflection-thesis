#!/bin/bash
#SBATCH --job-name=pair-route
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:20:00
#SBATCH --gres=gpu:1
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_route_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_route_v1/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_route_v1
$SIM_PY -B route_prepare.py
$SIM_PY -B route_worker.py
