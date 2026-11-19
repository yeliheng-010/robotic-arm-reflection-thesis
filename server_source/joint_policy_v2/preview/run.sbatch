#!/bin/bash
#SBATCH --job-name=generic-joint-gpu-zero-motion
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:12:00
#SBATCH --output=/home/yeliheng/grasp_server/joint_policy_v2/preview/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/joint_policy_v2/environment.sh
cd /home/yeliheng/grasp_server/joint_policy_v2/preview
$SIM_PY -B test_runtime.py
$SIM_PY -B prepare.py
timeout 180 $SIM_PY -B entry.py old_964008
timeout 180 $SIM_PY -B entry.py new_964345
