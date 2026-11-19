#!/bin/bash
#SBATCH --job-name=waypoint-static
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_route_v2/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_route_v2/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_route_v2
$SIM_PY -B waypoint_preflight.py
