#!/bin/bash
#SBATCH --job-name=bounded-ik-scope-fix
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/natural_joint_guard_v1/probe-v2-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_self_route_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/natural_joint_guard_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/natural_joint_guard_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B probe_v2.py
