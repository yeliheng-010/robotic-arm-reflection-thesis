#!/bin/bash
#SBATCH --job-name=rrt-unit-tests
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:02:00
#SBATCH --output=/home/yeliheng/grasp_server/joint_search_v1/test-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/pregrasp_route_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/joint_search_v1/test_rrt.py
