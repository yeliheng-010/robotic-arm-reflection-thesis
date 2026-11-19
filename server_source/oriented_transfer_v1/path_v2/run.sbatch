#!/bin/bash
#SBATCH --job-name=oriented-held-path-support-escape
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:23:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/path_v2/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/oriented_transfer_v1/path_v2:/home/yeliheng/grasp_server/oriented_transfer_v1/path:$PYTHONPATH
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/path_v2/test_support.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/path_v2/register_v2.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/path_v2/run.py
