#!/bin/bash
#SBATCH --job-name=visual-unconsumed-v5
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_safe_visual_loop_v1/resume-v5-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_safe_visual_loop_v1/environment_v4.sh
cd /home/yeliheng/grasp_server/ai_safe_visual_loop_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_observation_reference_v5 test_strategy test_actions test_labels test_span_gate -v
/home/yeliheng/grasp_server/env_sim/bin/python -B resume_v5.py
