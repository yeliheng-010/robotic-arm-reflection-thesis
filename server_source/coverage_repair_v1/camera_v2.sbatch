#!/bin/bash
#SBATCH --job-name=coverage-camera-v2
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/coverage_repair_v1/camera-v2-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/coverage_repair_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/test_registration.py
$SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/camera_runner_v2.py prepare
timeout 240 $SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/camera_runner_v2.py probe
timeout 240 $SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/camera_runner_v2.py audit
$SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/review.py
