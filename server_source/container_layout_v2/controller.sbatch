#!/bin/bash
#SBATCH --job-name=layout-controller
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=09:00:00
#SBATCH --output=/home/yeliheng/grasp_server/container_layout_v2/controller-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/container_layout_v2/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/container_layout_v2/controller.py
