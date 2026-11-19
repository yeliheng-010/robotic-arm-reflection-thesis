#!/bin/bash
#SBATCH --job-name=closed_loop
#SBATCH --partition=batch
#SBATCH --gres=gpu:v100:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=40G
#SBATCH --time=02:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/stability_20261019/closed-loop-%j.log
set -euo pipefail
source training/server/qwen35_env.sh
export MUJOCO_GL=egl MPLCONFIGDIR=/tmp/grasp-stability PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/yeliheng/grasp_server/stability_20261019:/home/yeliheng/grasp_server/geometry_20261019:.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/home/yeliheng/grasp_server/env_sim/bin/python -m stability.loop_run
