#!/bin/bash
#SBATCH --job-name=depth-sampling
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/depth_diagnostic_v1/sampling-%j.log
#SBATCH --gres=gpu:1
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 150 $SIM_PY -B -m depth_diagnostic_v1.sampling
