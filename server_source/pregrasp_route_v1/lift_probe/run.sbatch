#!/bin/bash
#SBATCH --job-name=raised-pregrasp-readonly
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:08:00
#SBATCH --output=/home/yeliheng/grasp_server/pregrasp_route_v1/lift_probe/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/pregrasp_route_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/pregrasp_route_v1/lift_probe/lp_probe.py
