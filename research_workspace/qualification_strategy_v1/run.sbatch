#!/bin/bash
#SBATCH --job-name=strategy-qualification-probe
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/qualification_strategy_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/qualification_strategy_v1/environment.sh
cd /home/yeliheng/grasp_server/qualification_strategy_v1
$SIM_PY -B qs_prepare.py
$SIM_PY -B qs_run.py
