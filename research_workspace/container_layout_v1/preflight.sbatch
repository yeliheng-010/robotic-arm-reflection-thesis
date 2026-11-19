#!/bin/bash
#SBATCH --job-name=layout-preflight
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/container_layout_v1/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/container_layout_v1/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/container_layout_v1/cl_preflight.py
