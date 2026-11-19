#!/bin/bash
#SBATCH --job-name=held-view-preflight
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/held_observation_v1/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m unittest held_observation_v1.test_pause held_observation_v1.test_geometry -v
$SIM_PY -B -m held_observation_v1.worker prepare
timeout 180 $SIM_PY -B -m held_observation_v1.worker preflight
timeout 180 $SIM_PY -B -m held_observation_v1.audit preflight
