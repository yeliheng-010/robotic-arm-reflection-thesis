#!/bin/bash
#SBATCH --job-name=actual-sensing-plan-only
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/qualification_strategy_v1/actual-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/qualification_strategy_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/qualification_strategy_v1/qa_run.py
