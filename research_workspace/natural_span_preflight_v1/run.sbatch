#!/bin/bash
#SBATCH --job-name=observable-qualification
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/home/yeliheng/grasp_server/natural_span_preflight_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/natural_qualified_pilot_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/natural_span_preflight_v1:/home/yeliheng/grasp_server/natural_span_guard_v1:/home/yeliheng/grasp_server/natural_grasp_span_audit_v1:/home/yeliheng/grasp_server/natural_feasibility_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/natural_span_preflight_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B prepare.py
/home/yeliheng/grasp_server/env_sim/bin/python -B run.py
