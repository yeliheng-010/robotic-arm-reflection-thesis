#!/bin/bash
#SBATCH --job-name=targeted-branch-audit
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/targeted_collection_v1/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/targeted_collection_v1/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/targeted_collection_v1/report.py "$1"
