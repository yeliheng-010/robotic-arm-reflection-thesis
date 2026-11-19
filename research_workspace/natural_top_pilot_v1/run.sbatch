#!/bin/bash
#SBATCH --job-name=observed-top-capability-pilot
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=03:00:00
#SBATCH --output=/home/yeliheng/grasp_server/natural_top_pilot_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/natural_top_pilot_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/natural_top_pilot_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/natural_top_pilot_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B prepare.py
/home/yeliheng/grasp_server/env_sim/bin/python -B controller.py
