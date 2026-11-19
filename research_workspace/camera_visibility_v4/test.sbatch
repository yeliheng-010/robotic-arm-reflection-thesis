#!/bin/bash
#SBATCH --job-name=camera-visibility-tests
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/camera_visibility_v4/test-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/camera_visibility_v4/environment.sh
cd /home/yeliheng/grasp_server/camera_visibility_v4
$SIM_PY -B -m unittest discover -v
