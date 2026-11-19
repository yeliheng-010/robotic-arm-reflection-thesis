#!/bin/bash
#SBATCH --job-name=cd-model
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --output=/home/yeliheng/grasp_server/container_decision_diagnostic_v1/model-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/container_decision_diagnostic_v1/environment.sh
cd /home/yeliheng/grasp_server/container_decision_diagnostic_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python model_run.py
