#!/bin/bash
#SBATCH --job-name=private-collision-detail
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/qualification_strategy_v1/collision_detail/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/qualification_strategy_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/qualification_strategy_v1/collision_detail/cd_probe.py
