#!/bin/bash
#SBATCH --job-name=reflection-regression
#SBATCH --partition=batch
#SBATCH --gres=gpu:v100:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=16G
#SBATCH --time=06:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/refinement_v1/physical-%j.log
set -euo pipefail
source training/server/qwen35_env.sh
source /home/yeliheng/grasp_server/refinement_v1/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python -m refinement.run --mode "${1:?mode required}"
