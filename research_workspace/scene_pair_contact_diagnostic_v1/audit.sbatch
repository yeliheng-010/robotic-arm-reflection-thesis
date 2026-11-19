#!/bin/bash
#SBATCH --job-name=contact-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_contact_diagnostic_v1/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_candidates_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/scene_pair_contact_diagnostic_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/scene_pair_contact_diagnostic_v1
$SIM_PY diagnostic_audit.py
