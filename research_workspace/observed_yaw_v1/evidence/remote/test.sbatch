#!/bin/bash
#SBATCH --job-name=observed-yaw-tests
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=3G
#SBATCH --time=00:02:00
#SBATCH --output=/home/yeliheng/grasp_server/observed_yaw_v1/test-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/joint_policy_v2/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/observed_yaw_v1/test_yaw.py
