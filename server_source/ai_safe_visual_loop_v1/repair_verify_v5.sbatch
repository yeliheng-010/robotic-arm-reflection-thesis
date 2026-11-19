#!/bin/bash
#SBATCH --job-name=visual-audit-reference-v5
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_safe_visual_loop_v1/repair-verify-v5-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_safe_visual_loop_v1/environment_v4.sh
cd /home/yeliheng/grasp_server/ai_safe_visual_loop_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_observation_reference_v5 -v
/home/yeliheng/grasp_server/env_sim/bin/python -B audit_v5.py --case-id A0_962905_varied_noisy
