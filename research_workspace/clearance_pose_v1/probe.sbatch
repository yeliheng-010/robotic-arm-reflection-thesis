#!/bin/bash
#SBATCH --job-name=clearance-actual-snapshot-probe
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/clearance_pose_v1/probe-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/clearance_pose_v1/environment.sh
cd /home/yeliheng/grasp_server/clearance_pose_v1
$SIM_PY -B -m unittest discover -v
$SIM_PY -B cp_run.py
