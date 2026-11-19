#!/bin/bash
#SBATCH --job-name=sensor-independent-run
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/sensor_independent_v2/run-%A_%a.log
#SBATCH --gres=gpu:1
#SBATCH --array=0-11%2
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 560 $SIM_PY -B -m sensor_independent_v2.worker
