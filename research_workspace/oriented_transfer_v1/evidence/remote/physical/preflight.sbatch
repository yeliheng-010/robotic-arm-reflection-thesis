#!/bin/bash
#SBATCH --job-name=oriented-gpu-preview
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:08:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/physical/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/physical/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/physical/test_commands.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/physical/op_worker.py prepare
timeout 300 $SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/physical/op_worker.py preflight
