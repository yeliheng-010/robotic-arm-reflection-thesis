#!/bin/bash
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_candidates_v1/unit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_candidates_v1/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_candidates_v1
$SIM_PY -m unittest discover -v
