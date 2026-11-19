#!/bin/bash
#SBATCH --job-name=layout-audit
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/container_layout_v2/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/container_layout_v2/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/container_layout_v2/cl_report.py "$1"
