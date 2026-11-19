#!/bin/bash
#SBATCH --job-name=waypoint-full-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_route_v2/full-audit-%j.log
# 仅供未来实际完成完整路径/物理执行的独立版本使用，本轮不提交。
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_route_v2/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_route_v2
$SIM_PY -B -m unittest discover -v
$SIM_PY -B waypoint_audit_refined.py
