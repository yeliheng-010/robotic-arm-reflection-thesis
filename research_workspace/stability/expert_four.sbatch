#!/bin/bash
#SBATCH --job-name=expert_four
#SBATCH --partition=batch
#SBATCH --gres=gpu:svc:2,gpu:v100:2
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=7-00:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/stability_20261019/expert-four-%j.log
set -euo pipefail
export MUJOCO_GL=egl MPLCONFIGDIR=/tmp/grasp-stability PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/yeliheng/grasp_server/stability_20261019:/home/yeliheng/grasp_server/geometry_20261019:.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
runtime=/home/yeliheng/grasp_server/env_sim/bin/python
"$runtime" -m stability.parallel_collect "$@"
