#!/bin/bash
#SBATCH --job-name=camera-light-occlusion
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/camera_visibility_v4/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/camera_visibility_v4/environment.sh
cd /home/yeliheng/grasp_server/camera_visibility_v4
$SIM_PY -B -m unittest discover -v
$SIM_PY -B run.py
