#!/bin/bash
#SBATCH --job-name=held-path-policy-tests
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/path/test-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/oriented_transfer_v1/path:$PYTHONPATH
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/path/test_policy.py
