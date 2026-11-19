#!/bin/bash
#SBATCH --job-name=visual-service-evidence
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_visual_service_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/natural_qualified_pilot_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/ai_visual_service_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/ai_visual_service_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B prepare.py
/home/yeliheng/grasp_server/env_sim/bin/python -B client_run.py
