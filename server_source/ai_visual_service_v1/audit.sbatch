#!/bin/bash
#SBATCH --job-name=visual-service-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_visual_service_v1/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/natural_qualified_pilot_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/ai_visual_service_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/ai_visual_service_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B audit.py
