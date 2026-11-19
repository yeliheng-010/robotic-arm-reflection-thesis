#!/bin/bash
#SBATCH --job-name=qualified-natural-pilot
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/natural_qualified_pilot_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/natural_qualified_pilot_v1/environment.sh
cd /home/yeliheng/grasp_server/natural_qualified_pilot_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B qp_controller.py
