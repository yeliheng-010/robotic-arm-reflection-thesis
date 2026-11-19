#!/bin/bash
#SBATCH --job-name=natural-lift-probe
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/natural_lift_probe_v1/probe-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_natural_loop_v1/environment.sh
cd /home/yeliheng/grasp_server/natural_lift_probe_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B probe_lift.py
