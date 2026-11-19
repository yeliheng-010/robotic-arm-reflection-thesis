#!/bin/bash
#SBATCH --job-name=pair-framing
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_feasibility_v1/prepare-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_feasibility_v1/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_feasibility_v1
$SIM_PY sf_prepare.py
