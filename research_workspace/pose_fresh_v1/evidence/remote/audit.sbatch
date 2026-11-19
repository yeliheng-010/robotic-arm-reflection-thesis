#!/bin/bash
#SBATCH --job-name=pose-fresh-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/pose_fresh_v1/audit-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 240 $SIM_PY -B -m pose_fresh_v1.audit
