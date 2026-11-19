#!/bin/bash
#SBATCH --job-name=set-loop-model
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_diagnostic_v1/service-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_diagnostic_v1/environment.sh
/home/yeliheng/grasp_server/qwen35/env/bin/python /home/yeliheng/grasp_server/recovery_diagnostic_v1/model_service.py
