#!/bin/bash
#SBATCH --job-name=visual-finetune-code-checks
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_finetune_v1/verify-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_training_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_finetune_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B -m unittest test_gate test_update -v
/home/yeliheng/grasp_server/qwen35/env/bin/python -B -c 'import freeze, smoke, train; print("imports passed; no real model updates")'
