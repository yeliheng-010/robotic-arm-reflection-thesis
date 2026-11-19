#!/bin/bash
#SBATCH --job-name=sensor-rgb-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/sensor_rgb_diagnostic_v1/audit-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 150 $SIM_PY -B -m sensor_rgb_diagnostic_v1.audit
