#!/bin/bash
#SBATCH --job-name=camera-extra-six-layouts
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/camera_visibility_v6/extra-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/camera_visibility_v6/environment.sh
cd /home/yeliheng/grasp_server/camera_visibility_v6
$SIM_PY -B run_extra.py
