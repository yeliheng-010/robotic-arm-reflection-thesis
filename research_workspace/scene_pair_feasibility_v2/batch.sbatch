#!/bin/bash
#SBATCH --job-name=pair-framed-run
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --array=0-3%4
#SBATCH --time=01:00:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_feasibility_v2/batch-%A_%a.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_feasibility_v2/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_feasibility_v2
$SIM_PY sf_batch.py
