#!/bin/bash
#SBATCH --job-name=deeper-lift-static-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/natural_deeper_lift_audit_v1/probe-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/natural_qualified_pilot_v1/environment.sh
cd /home/yeliheng/grasp_server/natural_deeper_lift_audit_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B probe.py
