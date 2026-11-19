#!/bin/bash
#SBATCH --job-name=guard-scope
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:05:00
#SBATCH --gres=gpu:1
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_guard_v2/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_candidates_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/scene_pair_guard_v2:/home/yeliheng/grasp_server/scene_pair_guard_v1:/home/yeliheng/grasp_server/scene_pair_contact_diagnostic_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/scene_pair_guard_v2
$SIM_PY scope_run.py
