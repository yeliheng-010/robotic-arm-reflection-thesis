#!/bin/bash
#SBATCH --job-name=oriented-full-held-path
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:23:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/path/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/oriented_transfer_v1/path:$PYTHONPATH
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/path/test_policy.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/path/register.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/path/run.py
