#!/bin/bash
#SBATCH --job-name=generic-joint-regression
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:55:00
#SBATCH --output=/home/yeliheng/grasp_server/joint_policy_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/joint_policy_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/joint_policy_v1/test_policy.py
$SIM_PY -B /home/yeliheng/grasp_server/joint_policy_v1/jg_register.py
$SIM_PY -B /home/yeliheng/grasp_server/joint_policy_v1/jg_run.py
