#!/bin/bash
#SBATCH --job-name=pregrasp-angle-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/joint_search_v1/validation/angles-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/joint_search_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/joint_search_v1/validation/angles_probe.py
