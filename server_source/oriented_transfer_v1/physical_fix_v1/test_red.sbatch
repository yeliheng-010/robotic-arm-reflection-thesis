#!/bin/bash
#SBATCH --job-name=oriented-wiring-red
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/physical_fix_v1/red-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/physical/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/oriented_transfer_v1/physical_fix_v1:$PYTHONPATH
export CARRY_IMPL=old
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/physical_fix_v1/test_wiring.py
