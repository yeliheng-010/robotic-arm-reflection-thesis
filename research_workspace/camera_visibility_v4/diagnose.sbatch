#!/bin/bash
#SBATCH --job-name=camera-render-diagnostic
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/camera_visibility_v4/diagnose-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/camera_visibility_v4/environment.sh
cd /home/yeliheng/grasp_server/camera_visibility_v4
$SIM_PY -B diagnose.py
