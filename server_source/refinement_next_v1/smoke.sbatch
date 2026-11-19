#!/bin/bash
#SBATCH --job-name=reflection-diagnostic-smoke
#SBATCH --partition=batch
#SBATCH --gres=gpu:v100:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/refinement_next_v1/smoke-%j.log
set -euo pipefail
source training/server/qwen35_env.sh
source /home/yeliheng/grasp_server/refinement_v3/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/refinement_next_v1:$PYTHONPATH
/home/yeliheng/grasp_server/env_sim/bin/python -m nextstudy.physical --index 0
/home/yeliheng/grasp_server/env_sim/bin/python -m nextstudy.physical --index 12
