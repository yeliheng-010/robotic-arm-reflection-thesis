#!/bin/bash
#SBATCH --job-name=round2_sft
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=40G
#SBATCH --time=04:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/stability_20261019/round2-train-%j.log
set -euo pipefail
source training/server/qwen35_env.sh
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/yeliheng/grasp_server/stability_20261019:/home/yeliheng/grasp_server/geometry_20261019:.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PYTHON=/home/yeliheng/grasp_server/qwen35/env/bin/python
"$PYTHON" -m round2.train --stop-after 1
"$PYTHON" -m round2.train --resume /home/yeliheng/grasp_server/stability_20261019/round2_sft_v1/checkpoint_00001
