#!/bin/bash
#SBATCH --job-name=pilot_validate
#SBATCH --partition=batch
#SBATCH --gres=gpu:v100:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=40G
#SBATCH --time=01:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/stability_20261019/pilot-validate-%j.log
set -euo pipefail
source training/server/qwen35_env.sh
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/yeliheng/grasp_server/stability_20261019:/home/yeliheng/grasp_server/geometry_20261019:.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/home/yeliheng/grasp_server/qwen35/env/bin/python -m stability.sft_validate
