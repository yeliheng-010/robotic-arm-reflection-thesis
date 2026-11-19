#!/bin/bash
#SBATCH --job-name=model-intent-schema-check
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:08:00
#SBATCH --output=/home/yeliheng/grasp_server/model_grasp_gpu_v3/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/model_grasp_gpu_v1/environment.sh
$SIM_PY -B -m unittest model_grasp_gpu_v3.test_prompt -v
$SIM_PY -B -m model_grasp_gpu_v3.register
source /home/yeliheng/grasp_server/candidate_sft_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server:/home/yeliheng/grasp_server/ai_visual_input_v1/torchvision_overlay:/home/yeliheng/grasp_server/ai_visual_input_v1:/home/yeliheng/grasp_server/ai_diagnosis_failure_v1:/home/yeliheng/grasp_server/ai_diagnosis_v1:$PYTHONPATH
/home/yeliheng/grasp_server/qwen35/env/bin/python -B -m model_grasp_gpu_v3.entry tokens
