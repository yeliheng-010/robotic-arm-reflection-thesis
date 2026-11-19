#!/bin/bash
#SBATCH --job-name=ai-failure-one-case
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_diagnosis_failure_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_diagnosis_failure_v1/environment.sh
cd /home/yeliheng/grasp_server/ai_diagnosis_failure_v1
$SIM_PY -B f_run.py
