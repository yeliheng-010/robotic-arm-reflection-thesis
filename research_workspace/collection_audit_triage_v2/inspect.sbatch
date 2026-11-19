#!/bin/bash
#SBATCH --job-name=recovery-state-triage-v2
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/collection_audit_triage_v2/inspect-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
export RECOVERY_BATCH=6
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/collection_audit_triage_v2
/home/yeliheng/grasp_server/env_sim/bin/python -B inspect_state.py
