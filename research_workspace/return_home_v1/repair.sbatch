#!/bin/bash
#SBATCH --job-name=return-home-physical-repair
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/return_home_v1/repair-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/return_home_v1/environment.sh
cd /home/yeliheng/grasp_server/return_home_v1
$SIM_PY -B -m unittest discover -v
$SIM_PY -B rh_verify.py
$SIM_PY -B rh_prepare.py
$SIM_PY -B rh_run.py
