#!/bin/bash
#SBATCH --job-name=bounded-rrt-readonly
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:25:00
#SBATCH --output=/home/yeliheng/grasp_server/joint_search_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/joint_search_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/joint_search_v1/test_rrt.py
$SIM_PY -B /home/yeliheng/grasp_server/joint_search_v1/js_probe.py
timeout 180 $SIM_PY -B /home/yeliheng/grasp_server/joint_search_v1/js_audit.py full
timeout 180 $SIM_PY -B /home/yeliheng/grasp_server/joint_search_v1/js_audit.py audit
