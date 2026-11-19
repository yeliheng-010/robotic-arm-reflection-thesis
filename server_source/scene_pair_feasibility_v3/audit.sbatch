#!/bin/bash
#SBATCH --job-name=pair-framed-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_feasibility_v3/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_feasibility_v3/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_feasibility_v3
$SIM_PY sf_audit.py
