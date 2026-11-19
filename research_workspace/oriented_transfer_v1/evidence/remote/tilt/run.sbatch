#!/bin/bash
#SBATCH --job-name=oriented-tilt-endpoints
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:23:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/tilt/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/oriented_transfer_v1/tilt:$PYTHONPATH
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/tilt/test_tilt.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/tilt/register.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/tilt/run.py
