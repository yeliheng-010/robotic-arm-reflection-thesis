#!/bin/bash
#SBATCH --job-name=reflection-guided-semantics
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=01:30:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/refinement_next_v1/semantic-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/refinement_v3/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/refinement_next_v1:$PYTHONPATH
/home/yeliheng/grasp_server/env_sim/bin/python -m nextstudy.probe
