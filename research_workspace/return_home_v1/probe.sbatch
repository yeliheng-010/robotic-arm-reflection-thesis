#!/bin/bash
#SBATCH --job-name=return-home-readonly-probe
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/return_home_v1/probe-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/return_home_v1/environment.sh
cd /home/yeliheng/grasp_server/return_home_v1
$SIM_PY -B -m unittest discover -v
$SIM_PY -B rh_probe.py
