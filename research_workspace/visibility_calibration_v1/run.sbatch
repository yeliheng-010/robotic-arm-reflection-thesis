#!/bin/bash
#SBATCH --job-name=visibility-calibration-v1
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/visibility_calibration_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m unittest visibility_calibration_v1.test_policy visibility_calibration_v1.test_analysis held_observation_v1.test_geometry -v
timeout 900 $SIM_PY -B -m visibility_calibration_v1.worker
timeout 180 $SIM_PY -B -m visibility_calibration_v1.audit
