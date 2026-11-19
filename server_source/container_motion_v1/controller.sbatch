#!/bin/bash
#SBATCH --job-name=cm-controller
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=07:00:00
#SBATCH --output=/home/yeliheng/grasp_server/container_motion_v1/controller-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/container_motion_v1/environment.sh
cd /home/yeliheng/grasp_server/container_motion_v1
/home/yeliheng/grasp_server/env_sim/bin/python controller.py
