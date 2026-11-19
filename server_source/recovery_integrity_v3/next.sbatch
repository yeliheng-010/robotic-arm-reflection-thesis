#!/bin/bash
#SBATCH --job-name=recovery-next-integrity-v3
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_integrity_v3/next-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_integrity_v3
/home/yeliheng/grasp_server/env_sim/bin/python -B iv3_next.py
