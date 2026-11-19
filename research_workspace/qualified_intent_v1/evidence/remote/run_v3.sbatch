#!/bin/bash
#SBATCH --job-name=qualified-grasp-intent-v3
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_intent_v1/run-v3-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m qualified_intent_v1.model_v3 prepare
source /home/yeliheng/grasp_server/candidate_sft_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server:/home/yeliheng/grasp_server/ai_visual_input_v1/torchvision_overlay:/home/yeliheng/grasp_server/ai_visual_input_v1:/home/yeliheng/grasp_server/ai_diagnosis_failure_v1:/home/yeliheng/grasp_server/ai_diagnosis_v1:$PYTHONPATH
timeout 800 /home/yeliheng/grasp_server/qwen35/env/bin/python -B -m qualified_intent_v1.model_v3 run
