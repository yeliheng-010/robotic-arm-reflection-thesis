#!/bin/bash
#SBATCH --job-name=model-intent-zero-motion
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/model_grasp_gpu_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/model_grasp_gpu_v1/environment.sh
$SIM_PY -B -m model_grasp_gpu_v1.controller
$SIM_PY -B -m model_grasp_gpu_v1.audit
