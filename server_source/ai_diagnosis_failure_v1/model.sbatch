#!/bin/bash
#SBATCH --job-name=ai-failure-model-two
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_diagnosis_failure_v1/model-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/candidate_sft_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/ai_diagnosis_failure_v1:/home/yeliheng/grasp_server/ai_diagnosis_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/ai_diagnosis_failure_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B f_model.py
