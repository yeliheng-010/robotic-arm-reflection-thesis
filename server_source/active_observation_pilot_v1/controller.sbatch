#!/bin/bash
#SBATCH --job-name=active-controller
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=04:30:00
#SBATCH --output=/home/yeliheng/grasp_server/active_observation_pilot_v1/controller-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/active_observation_pilot_v1/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/active_observation_pilot_v1/controller.py
