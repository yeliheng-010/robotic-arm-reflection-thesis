#!/bin/bash
#SBATCH --job-name=pregrasp-endpoint-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/pregrasp_route_v1/lift_probe/endpoints-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/pregrasp_route_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/pregrasp_route_v1/lift_probe/ep_inspect.py
