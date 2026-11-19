#!/bin/bash
#SBATCH --job-name=visual-reservation-requalify
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/home/yeliheng/grasp_server/safe_visual_qualification_v2/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/natural_span_pilot_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/safe_visual_qualification_v2:/home/yeliheng/grasp_server/natural_span_preflight_v1:/home/yeliheng/grasp_server/natural_feasibility_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/safe_visual_qualification_v2
/home/yeliheng/grasp_server/env_sim/bin/python -B run.py
