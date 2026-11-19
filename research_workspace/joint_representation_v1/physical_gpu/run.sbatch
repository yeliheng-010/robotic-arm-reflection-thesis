#!/bin/bash
#SBATCH --job-name=joint-equivalent-gpu-single
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:12:00
#SBATCH --output=/home/yeliheng/grasp_server/joint_representation_v1/physical_gpu/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/joint_representation_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/joint_representation_v1/physical:$PYTHONPATH
cd /home/yeliheng/grasp_server/joint_representation_v1/physical_gpu
$SIM_PY -B gpu_worker.py prepare
timeout 180 $SIM_PY -B gpu_worker.py preflight
timeout 300 $SIM_PY -B gpu_worker.py execute
timeout 180 $SIM_PY -B gpu_worker.py audit
