#!/bin/bash
#SBATCH --job-name=oriented-release-endpoints
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:42:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/test_geometry.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/test_volume.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/ot_register.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/ot_run.py
