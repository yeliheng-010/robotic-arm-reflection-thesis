#!/bin/bash
#SBATCH --job-name=model-intent-preflight
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:08:00
#SBATCH --output=/home/yeliheng/grasp_server/model_grasp_gpu_v1/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/model_grasp_gpu_v1/environment.sh
$SIM_PY -B -m unittest model_grasp_gpu_v1.test_observed -v
$SIM_PY -B -m model_grasp_gpu_v1.register
$SIM_PY -B -m model_grasp_gpu_v1.preflight
