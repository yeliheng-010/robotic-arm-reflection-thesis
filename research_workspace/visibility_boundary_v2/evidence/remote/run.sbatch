#!/bin/bash
#SBATCH --job-name=visibility-boundary-v2
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:06:00
#SBATCH --output=/home/yeliheng/grasp_server/visibility_boundary_v2/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
timeout 240 $SIM_PY -B -m visibility_boundary_v2.worker
timeout 90 $SIM_PY -B -m visibility_boundary_v2.audit
