#!/bin/bash
#SBATCH --job-name=recovery-integrity-v2-merge
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_integrity_v2/merge-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_integrity_v2
/home/yeliheng/grasp_server/env_sim/bin/python -B ig_merge.py
