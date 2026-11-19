#!/bin/bash
#SBATCH --job-name=camera-collection-test
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/camera_collection_v1/test-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/camera_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/camera_collection_v1
$SIM_PY -B -m unittest discover -v
