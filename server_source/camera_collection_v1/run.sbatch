#!/bin/bash
#SBATCH --job-name=visible-camera-pilot
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=03:00:00
#SBATCH --output=/home/yeliheng/grasp_server/camera_collection_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/camera_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/camera_collection_v1
$SIM_PY -B -m unittest discover -v
$SIM_PY -B cc_verify.py
$SIM_PY -B cc_prepare.py
$SIM_PY -B cc_run.py
