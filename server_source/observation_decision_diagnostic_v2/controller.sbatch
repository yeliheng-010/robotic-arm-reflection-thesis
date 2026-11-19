#!/bin/bash
#SBATCH --job-name=od-controller
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=07:00:00
#SBATCH --output=/home/yeliheng/grasp_server/observation_decision_diagnostic_v2/controller-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/observation_decision_diagnostic_v2/environment.sh
cd /home/yeliheng/grasp_server/observation_decision_diagnostic_v2
/home/yeliheng/grasp_server/env_sim/bin/python controller.py
