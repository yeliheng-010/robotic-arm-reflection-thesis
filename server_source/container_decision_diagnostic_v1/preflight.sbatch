#!/bin/bash
#SBATCH --job-name=cd-preflight
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=3G
#SBATCH --time=02:00:00
#SBATCH --output=/home/yeliheng/grasp_server/container_decision_diagnostic_v1/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/container_decision_diagnostic_v1/environment.sh
cd /home/yeliheng/grasp_server/container_decision_diagnostic_v1
/home/yeliheng/grasp_server/env_sim/bin/python preflight.py
