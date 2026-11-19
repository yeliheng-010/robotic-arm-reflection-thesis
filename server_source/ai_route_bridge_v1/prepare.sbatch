#!/bin/bash
#SBATCH --job-name=ai-route-bridge-prepare
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_route_bridge_v1/prepare-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_route_bridge_v1/environment.sh
cd /home/yeliheng/grasp_server/ai_route_bridge_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B rb_prepare.py
