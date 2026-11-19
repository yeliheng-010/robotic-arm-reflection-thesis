#!/bin/bash
#SBATCH --job-name=tracking-public-facts
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_tracking_facts_v1/check-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_route_bridge_v2/environment.sh
cd /home/yeliheng/grasp_server/ai_tracking_facts_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B check.py
