#!/bin/bash
#SBATCH --job-name=paired-input-diagnosis
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:02:00
#SBATCH --output=/home/yeliheng/grasp_server/joint_representation_v1/diagnosis/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/joint_representation_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/joint_representation_v1/diagnosis/input_compare.py
