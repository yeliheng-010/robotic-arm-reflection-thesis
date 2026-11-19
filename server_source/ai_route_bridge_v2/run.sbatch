#!/bin/bash
#SBATCH --job-name=vertical-bridge-eight
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_route_bridge_v2/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_route_bridge_v2/environment.sh
cd /home/yeliheng/grasp_server/ai_route_bridge_v2
/home/yeliheng/grasp_server/env_sim/bin/python -B rv_controller.py
