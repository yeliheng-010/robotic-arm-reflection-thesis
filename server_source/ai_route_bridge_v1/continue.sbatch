#!/bin/bash
#SBATCH --job-name=ai-route-bridge-remaining
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_route_bridge_v1/continue-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_route_bridge_v1/environment.sh
cd /home/yeliheng/grasp_server/ai_route_bridge_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B rb_continue.py
