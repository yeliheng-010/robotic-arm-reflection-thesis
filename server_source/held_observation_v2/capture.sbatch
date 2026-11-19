#!/bin/bash
#SBATCH --job-name=held-view-v2-no-release
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:12:00
#SBATCH --output=/home/yeliheng/grasp_server/held_observation_v2/capture-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m held_observation_v2.worker register
timeout 360 $SIM_PY -B -m held_observation_v2.worker execute
timeout 240 $SIM_PY -B -m held_observation_v2.worker audit_physical
