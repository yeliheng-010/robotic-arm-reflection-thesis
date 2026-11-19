#!/bin/bash
#SBATCH --job-name=visual-adapter-comparison-checks
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_adapter_comparison_v1/verify-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_comparison_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_adapter_comparison_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B -m unittest test_pairs test_generator -v
/home/yeliheng/grasp_server/qwen35/env/bin/python -B verify.py
