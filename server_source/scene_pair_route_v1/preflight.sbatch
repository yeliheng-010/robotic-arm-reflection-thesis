#!/bin/bash
#SBATCH --job-name=pair-route-static
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_route_v1/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_route_v1/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_route_v1
$SIM_PY -B -m unittest discover -v
$SIM_PY -B route_preflight.py
