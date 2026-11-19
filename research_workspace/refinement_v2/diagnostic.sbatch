#!/bin/bash
#SBATCH --job-name=reflection-semantics
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=3G
#SBATCH --time=01:30:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/refinement_v2/diagnostic-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/refinement_v2/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python -m refinement.probe
