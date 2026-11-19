#!/bin/bash
#SBATCH --job-name=fresh-task-accuracy-paired
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=01:00:00
#SBATCH --output=/home/yeliheng/grasp_server/fresh_accuracy_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/fresh_accuracy_v1/environment.sh
cd /home/yeliheng/grasp_server/fresh_accuracy_v1
$SIM_PY -B -m unittest discover -v
$SIM_PY -B fa_verify.py
$SIM_PY -B fa_register.py
$SIM_PY -B fa_run.py
