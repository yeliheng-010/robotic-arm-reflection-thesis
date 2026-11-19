#!/bin/bash
#SBATCH --job-name=visual-adapter-prepare
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_adapter_comparison_v1/prepare-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_comparison_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_adapter_comparison_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B ac_prepare.py
