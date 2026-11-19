#!/bin/bash
#SBATCH --job-name=generic-entry-source-validation
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/joint_policy_v2/validation/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/joint_policy_v2/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/joint_policy_v2/validation/test_entry.py
$SIM_PY -B /home/yeliheng/grasp_server/joint_policy_v2/validation/source_check.py
