#!/bin/bash
#SBATCH --job-name=observed-top-historical-fit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/observed_top_pose_v1/probe-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/natural_span_pilot_v1/environment.sh
cd /home/yeliheng/grasp_server/observed_top_pose_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B probe.py
