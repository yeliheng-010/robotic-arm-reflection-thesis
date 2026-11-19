#!/bin/bash
#SBATCH --job-name=visible-camera-wiring-smoke
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/camera_collection_v1/smoke-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/camera_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/camera_collection_v1
$SIM_PY -B -m unittest discover -v
$SIM_PY -B cc_smoke.py
