#!/bin/bash
#SBATCH --job-name=expert_batch_v1
#SBATCH --partition=batch
#SBATCH --gres=gpu:v100:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=7-00:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/stability_20261019/expert-batch-%j.log
set -euo pipefail
export MUJOCO_GL=egl MPLCONFIGDIR=/tmp/grasp-stability PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/yeliheng/grasp_server/stability_20261019:/home/yeliheng/grasp_server/geometry_20261019:.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
runtime=/home/yeliheng/grasp_server/env_sim/bin/python
"$runtime" -m stability.expert_collect --stage batch --run expert_batch_v1
"$runtime" -m stability.expert_audit --run expert_batch_v1
