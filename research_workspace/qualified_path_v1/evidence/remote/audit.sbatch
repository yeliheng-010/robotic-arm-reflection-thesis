#!/bin/bash
#SBATCH --job-name=qualified-feedback-path-audit
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:09:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_path_v1/audit-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m qualified_feedback_v1.audit
$SIM_PY -B -m qualified_path_v1.audit
