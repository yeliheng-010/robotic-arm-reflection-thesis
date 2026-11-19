#!/bin/bash
#SBATCH --job-name=oriented-numeric-diagnosis
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/numeric-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/numeric_probe.py
