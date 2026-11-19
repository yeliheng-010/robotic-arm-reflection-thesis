#!/bin/bash
#SBATCH --job-name=sd-prepare
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_diversity_v2/prepare-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_diversity_v2/environment.sh
cd /home/yeliheng/grasp_server/scene_diversity_v2
$SIM_PY sd_preflight.py
$SIM_PY sd_render.py
