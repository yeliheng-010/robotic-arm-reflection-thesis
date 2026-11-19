#!/bin/bash
#SBATCH --job-name=ai-runtime-remaining
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_diagnosis_runtime_v1/resume-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_diagnosis_runtime_v1/environment.sh
cd /home/yeliheng/grasp_server/ai_diagnosis_runtime_v1
$SIM_PY -B live_resume.py
