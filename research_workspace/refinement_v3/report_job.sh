#!/bin/bash
#SBATCH --job-name=reflection-report
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:10:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/refinement_v3/report-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/refinement_v3/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/refinement_v3/finalize.py
