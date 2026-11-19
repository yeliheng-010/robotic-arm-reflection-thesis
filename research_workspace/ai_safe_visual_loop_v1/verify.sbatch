#!/bin/bash
#SBATCH --job-name=safe-visual-code-check
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_safe_visual_loop_v1/verify-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_safe_visual_loop_v1/environment.sh
cd /home/yeliheng/grasp_server/ai_safe_visual_loop_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B verify_code.py
