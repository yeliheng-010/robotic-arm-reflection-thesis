#!/bin/bash
#SBATCH --job-name=goal-geometry-check
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_route_v3/geometry-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_route_v3/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_route_v3
$SIM_PY -B geometry_diagnostic.py
