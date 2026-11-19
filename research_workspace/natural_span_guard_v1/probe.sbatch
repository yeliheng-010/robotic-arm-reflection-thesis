#!/bin/bash
#SBATCH --job-name=pose-span-guard-probe
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/natural_span_guard_v1/probe-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/natural_qualified_pilot_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/natural_span_guard_v1:/home/yeliheng/grasp_server/natural_grasp_span_audit_v1:$PYTHONPATH
cd /home/yeliheng/grasp_server/natural_span_guard_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B probe.py
