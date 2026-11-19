#!/bin/bash
#SBATCH --job-name=held-view-v3-preflight
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/held_observation_v3/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m unittest held_observation_v1.test_pause held_observation_v1.test_geometry held_observation_v2.test_capture held_observation_v3.test_policy -v
$SIM_PY -B -m held_observation_v3.worker prepare
$SIM_PY -B -m held_observation_v3.worker preflight
