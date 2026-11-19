#!/bin/bash
#SBATCH --job-name=oriented-held-volume-tests
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/volume-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/test_volume.py
