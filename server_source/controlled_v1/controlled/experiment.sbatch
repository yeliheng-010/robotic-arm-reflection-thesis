#!/bin/bash
#SBATCH --job-name=controlled-experiment
#SBATCH --partition=batch
#SBATCH --gres=gpu:v100:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=16G
#SBATCH --time=06:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/controlled_v1/experiment-%j.log
set -euo pipefail
source training/server/qwen35_env.sh
export PYTHONPATH=/home/yeliheng/grasp_server/controlled_v1:/home/yeliheng/grasp_server/diversity_v1:/home/yeliheng/grasp_server/flashnext_v1:/home/yeliheng/grasp_server/stability_20261019:/home/yeliheng/grasp_server/geometry_20261019:.
export MUJOCO_GL=egl MPLCONFIGDIR=/tmp/grasp-controlled PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/home/yeliheng/grasp_server/env_sim/bin/python -m controlled.run --mode smoke
/home/yeliheng/grasp_server/env_sim/bin/python -m controlled.run --mode pilot
