#!/bin/bash
#SBATCH --job-name=visual-adapter-comparison
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_adapter_comparison_v1/adapter-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_comparison_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_adapter_comparison_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B ac_run.py
/home/yeliheng/grasp_server/qwen35/env/bin/python -B ac_report.py
