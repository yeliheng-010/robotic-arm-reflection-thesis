#!/bin/bash
#SBATCH --job-name=sensor-independent-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/observation_search_v1/audit-merge-%A.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 560 $SIM_PY -B -m observation_search_v1.audit_merge
