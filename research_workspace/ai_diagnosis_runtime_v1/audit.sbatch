#!/bin/bash
#SBATCH --job-name=ai-runtime-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_diagnosis_runtime_v1/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_diagnosis_runtime_v1/environment.sh
cd /home/yeliheng/grasp_server/ai_diagnosis_runtime_v1
$SIM_PY -B audit_live.py
