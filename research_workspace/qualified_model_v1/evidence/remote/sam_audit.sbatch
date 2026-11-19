#!/bin/bash
#SBATCH --job-name=qualified-sam-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_model_v1/sam-audit-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m qualified_model_v1.sam_audit
