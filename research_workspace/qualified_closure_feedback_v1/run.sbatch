#!/bin/bash
#SBATCH --job-name=closure-model-feedback
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:25:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_feedback_v1/run-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 1440 $SIM_PY -B -m qualified_closure_feedback_v1.worker
