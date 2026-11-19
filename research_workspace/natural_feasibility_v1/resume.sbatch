#!/bin/bash
#SBATCH --job-name=natural-preflight-resume
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=01:00:00
#SBATCH --output=/home/yeliheng/grasp_server/natural_feasibility_v1/resume-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_self_route_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/natural_joint_guard_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/natural_feasibility_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B resume.py
