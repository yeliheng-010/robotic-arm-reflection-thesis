#!/bin/bash
#SBATCH --job-name=pair-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_validation_v1/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_validation_v1/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_validation_v1
$SIM_PY pv_audit.py
