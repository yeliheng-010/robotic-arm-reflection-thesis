#!/bin/bash
#SBATCH --job-name=sd-physics
#SBATCH --partition=batch
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --gres=gpu:1
#SBATCH --array=0-3%4
#SBATCH --time=02:00:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_diversity_v1/physics-%A_%a.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_diversity_v1/environment.sh
cd /home/yeliheng/grasp_server/scene_diversity_v1
$SIM_PY sd_run.py "$1"
