#!/bin/bash
#SBATCH --job-name=layout-recover-model
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=08:00:00
#SBATCH --output=/home/yeliheng/grasp_server/container_recovery_v1/service-%A_%a.log
#SBATCH --gres=gpu:1
set -euo pipefail
source /home/yeliheng/grasp_server/container_recovery_v1/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/container_recovery_v1/orchestrator.py
