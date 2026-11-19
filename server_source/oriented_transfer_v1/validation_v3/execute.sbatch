#!/bin/bash
#SBATCH --job-name=oriented-v3-single-physical
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:12:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/execute-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/worker.py register
timeout 360 $SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/worker.py execute
timeout 240 $SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/validation_v3/worker.py audit
test -f /home/yeliheng/grasp_server/oriented_transfer_v1/trial_gpu_v3/completion.json
