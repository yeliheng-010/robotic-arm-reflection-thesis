#!/bin/bash
#SBATCH --job-name=surface-audit-diagnose
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:08:00
#SBATCH --output=/home/yeliheng/grasp_server/surface_physical_audit_v2/diagnose-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m surface_physical_audit_v2.diagnose
