#!/bin/bash
#SBATCH --job-name=observed-surface-grasp
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/surface_grasp_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/model_grasp_gpu_v1/environment.sh
$SIM_PY -B -m unittest surface_grasp_v1.test_surface surface_grasp_v1.test_planning -v
$SIM_PY -B -m surface_grasp_v1.register
$SIM_PY -B -m surface_grasp_v1.endpoints probe
$SIM_PY -B -m surface_grasp_v1.endpoints audit
$SIM_PY -B -m surface_grasp_v1.paths probe
$SIM_PY -B -m surface_grasp_v1.paths audit
