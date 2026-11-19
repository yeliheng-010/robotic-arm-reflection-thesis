#!/bin/bash
#SBATCH --job-name=cd-model_audit
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=3G
#SBATCH --time=02:00:00
#SBATCH --output=/home/yeliheng/grasp_server/container_decision_diagnostic_v1/model_audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/container_decision_diagnostic_v1/environment.sh
cd /home/yeliheng/grasp_server/container_decision_diagnostic_v1
/home/yeliheng/grasp_server/env_sim/bin/python model_audit.py
