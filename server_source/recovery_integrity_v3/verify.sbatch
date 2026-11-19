#!/bin/bash
#SBATCH --job-name=recovery-integrity-v3-verify
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_integrity_v3/verify-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
export RECOVERY_BATCH=6
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_integrity_v3
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_integrity -v
/home/yeliheng/grasp_server/env_sim/bin/python -B verify.py
