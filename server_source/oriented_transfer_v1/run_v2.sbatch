#!/bin/bash
#SBATCH --job-name=oriented-release-unit-quaternion
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:23:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/run-v2-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/ot_validate.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/ot_register_v2.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/ot_run_v2.py
