#!/bin/bash
#SBATCH --job-name=visual-input-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_visual_audit_v1/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_route_bridge_v2/environment.sh
cd /home/yeliheng/grasp_server/ai_visual_audit_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B audit.py
