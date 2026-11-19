#!/bin/bash
#SBATCH --job-name=camera-visibility-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/camera_visibility_v5/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/camera_visibility_v5/environment.sh
cd /home/yeliheng/grasp_server/camera_visibility_v5
$SIM_PY -B audit.py
