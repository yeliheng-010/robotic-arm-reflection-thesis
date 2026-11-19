#!/bin/bash
#SBATCH --job-name=oriented-v3-budget-red
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:02:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/red-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/test_gate.py
