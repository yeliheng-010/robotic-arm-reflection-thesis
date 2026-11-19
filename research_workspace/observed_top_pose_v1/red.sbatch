#!/bin/bash
#SBATCH --job-name=observed-top-red
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/observed_top_pose_v1/red-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/natural_span_pilot_v1/environment.sh
cd /home/yeliheng/grasp_server/observed_top_pose_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_fit -v
