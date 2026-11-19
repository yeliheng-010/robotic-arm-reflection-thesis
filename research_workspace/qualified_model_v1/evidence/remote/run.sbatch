#!/bin/bash
#SBATCH --job-name=qualified-image-grounding
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:12:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_model_v1/run-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m unittest qualified_model_v1.test_policy -v
$SIM_PY -B -m qualified_model_v1.prepare
source /home/yeliheng/grasp_server/candidate_sft_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server:/home/yeliheng/grasp_server/ai_visual_input_v1/torchvision_overlay:/home/yeliheng/grasp_server/ai_visual_input_v1:/home/yeliheng/grasp_server/ai_diagnosis_failure_v1:/home/yeliheng/grasp_server/ai_diagnosis_v1:$PYTHONPATH
timeout 640 /home/yeliheng/grasp_server/qwen35/env/bin/python -B -m qualified_model_v1.model
