#!/bin/bash
#SBATCH --job-name=round2_validate
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=20G
#SBATCH --time=04:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/stability_20261019/round2-validate-%j.log
set -euo pipefail
source training/server/qwen35_env.sh
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/yeliheng/grasp_server/stability_20261019:/home/yeliheng/grasp_server/geometry_20261019:.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/home/yeliheng/grasp_server/qwen35/env/bin/python -m round2.validate "$@"
