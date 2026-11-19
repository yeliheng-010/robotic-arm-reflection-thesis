#!/bin/bash
#SBATCH --job-name=multimodal-public-boundary
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_multimodal_requests_v1/check-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_self_route_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/ai_multimodal_requests_v1:/home/yeliheng/grasp_server/ai_tracking_facts_v1:/home/yeliheng/grasp_server/ai_observable_facts_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/ai_multimodal_requests_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B check.py
