#!/bin/bash
#SBATCH --job-name=pregrasp-joint-route-probe
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:40:00
#SBATCH --output=/home/yeliheng/grasp_server/pregrasp_route_v1/probe-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/pregrasp_route_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/pregrasp_route_v1/pg_run.py
