#!/bin/bash
#SBATCH --job-name=clearance-candidate-tests
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/clearance_pose_v1/test-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/clearance_pose_v1/environment.sh
cd /home/yeliheng/grasp_server/clearance_pose_v1
$SIM_PY -B -m unittest discover -v
