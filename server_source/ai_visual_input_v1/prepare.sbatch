#!/bin/bash
#SBATCH --job-name=visual-input-prepare
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_visual_input_v1/prepare-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_route_bridge_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/ai_visual_input_v1:/home/yeliheng/grasp_server/ai_observable_facts_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/ai_visual_input_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B mm_prepare.py
