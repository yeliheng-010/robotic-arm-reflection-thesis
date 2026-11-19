#!/bin/bash
#SBATCH --job-name=observed-long-capsule-probe
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:22:00
#SBATCH --output=/home/yeliheng/grasp_server/observed_long_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/observed_long_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/observed_long_v1/test_long.py
$SIM_PY -B /home/yeliheng/grasp_server/observed_long_v1/lc_register.py
$SIM_PY -B /home/yeliheng/grasp_server/observed_long_v1/lc_run.py
