#!/bin/bash
#SBATCH --job-name=oriented-gpu-single-physical
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/physical/execute-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/physical/environment.sh
$SIM_PY -B -c 'from reflection.__main__ import bootstrap; bootstrap(); import op_audit; import op_runtime'
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/physical/execution_register.py
timeout 360 $SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/physical/op_worker.py execute
timeout 240 $SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/physical/op_audit.py
test -f /home/yeliheng/grasp_server/oriented_transfer_v1/trial_gpu/audit.json
