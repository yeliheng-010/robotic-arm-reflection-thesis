#!/bin/bash
#SBATCH --job-name=task-accuracy-input-identity
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/task_accuracy_v1/analysis/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/task_accuracy_v1/environment.sh
cd /home/yeliheng/grasp_server/task_accuracy_v1
$SIM_PY -B analysis/input_compare.py
