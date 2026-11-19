#!/bin/bash
#SBATCH --job-name=held-view-readonly-review
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/held_observation_review_v1/review-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
timeout 180 $SIM_PY -B -m held_observation_review_v1.worker
