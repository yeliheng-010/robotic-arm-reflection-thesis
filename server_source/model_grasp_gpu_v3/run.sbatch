#!/bin/bash
#SBATCH --job-name=model-intent-scalar-zero-motion
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/model_grasp_gpu_v3/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/model_grasp_gpu_v1/environment.sh
$SIM_PY -B -m model_grasp_gpu_v3.entry controller
$SIM_PY -B -m model_grasp_gpu_v3.entry audit
