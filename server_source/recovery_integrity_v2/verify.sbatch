#!/bin/bash
#SBATCH --job-name=recovery-integrity-v2-verify
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_integrity_v2/verify-%j.log
set -euo pipefail
export RECOVERY_BATCH=4
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_integrity_v2
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_geometry test_policy -v
/home/yeliheng/grasp_server/env_sim/bin/python -B verify.py
