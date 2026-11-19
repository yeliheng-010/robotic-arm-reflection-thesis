#!/bin/bash
#SBATCH --job-name=visual-strategy-interface-check
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_safe_visual_loop_v1/verify-v4-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_safe_visual_loop_v1/environment_v4.sh
cd /home/yeliheng/grasp_server/ai_safe_visual_loop_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B verify_code_v4.py
