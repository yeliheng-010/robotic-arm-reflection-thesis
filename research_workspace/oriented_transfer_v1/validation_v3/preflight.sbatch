#!/bin/bash
#SBATCH --job-name=oriented-v3-gpu-preflight
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/test_gate.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/review.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/worker.py prepare
timeout 180 $SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/worker.py preflight
test -f /home/yeliheng/grasp_server/oriented_transfer_v1/trial_gpu_v3/preflight_result.json
