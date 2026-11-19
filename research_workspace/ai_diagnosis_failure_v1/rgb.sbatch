#!/bin/bash
#SBATCH --job-name=ai-failure-rgb-read
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_diagnosis_failure_v1/rgb-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_diagnosis_failure_v1/environment.sh
cd /home/yeliheng/grasp_server/ai_diagnosis_failure_v1
$SIM_PY -B f_rgb_diagnostic.py
