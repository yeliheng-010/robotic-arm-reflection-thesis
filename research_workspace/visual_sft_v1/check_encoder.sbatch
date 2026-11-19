#!/bin/bash
#SBATCH --job-name=visual-sft-encoding-only
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_sft_v1/encoder-check-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/candidate_sft_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/visual_sft_v1:/home/yeliheng/grasp_server/ai_visual_input_v1/torchvision_overlay:/home/yeliheng/grasp_server/ai_diagnosis_failure_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/visual_sft_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B check_encoder.py
