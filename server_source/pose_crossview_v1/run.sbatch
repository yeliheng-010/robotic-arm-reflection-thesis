#!/bin/bash
#SBATCH --job-name=pose-crossview-v1
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/pose_crossview_v1/run-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 60 $SIM_PY -B -m pose_crossview_v1.run
timeout 60 $SIM_PY -B -m pose_crossview_v1.audit
