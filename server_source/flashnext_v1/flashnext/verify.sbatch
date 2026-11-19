#!/bin/bash
#SBATCH --job-name=flashnext_verify
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/flashnext_v1/verify-%j.log
set -euo pipefail
export PYTHONPATH=/home/yeliheng/grasp_server/flashnext_v1:/home/yeliheng/grasp_server/stability_20261019:/home/yeliheng/grasp_server/geometry_20261019:.
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/flashnext_v1/verify.py

