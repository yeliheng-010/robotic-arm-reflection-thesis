#!/bin/bash
#SBATCH --job-name=visual-dataset-full-encoding
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_dataset_audit_v1/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_training_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_dataset_audit_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B audit.py
