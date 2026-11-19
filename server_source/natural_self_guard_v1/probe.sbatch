#!/bin/bash
#SBATCH --job-name=self-guard-static-probe
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/natural_self_guard_v1/probe-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_route_bridge_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/natural_self_guard_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/natural_self_guard_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B probe.py
