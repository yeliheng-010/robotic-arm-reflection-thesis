#!/bin/bash
#SBATCH --job-name=surface-single-physical
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:12:00
#SBATCH --output=/home/yeliheng/grasp_server/surface_physical_v1/execute-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m surface_physical_v1.worker register
set +e
timeout 360 $SIM_PY -B -m surface_physical_v1.worker execute
execution_code=$?
set -e
timeout 240 $SIM_PY -B -m surface_physical_v1.audit physical
exit "$execution_code"
