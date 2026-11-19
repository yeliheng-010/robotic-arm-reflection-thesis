#!/bin/bash
#SBATCH --job-name=od-audit
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/observation_decision_diagnostic_v2/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/observation_decision_diagnostic_v2/environment.sh
cd /home/yeliheng/grasp_server/observation_decision_diagnostic_v2
/home/yeliheng/grasp_server/env_sim/bin/python report.py "$1"
