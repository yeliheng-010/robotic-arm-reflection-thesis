#!/bin/bash
#SBATCH --job-name=recovery-audit-failure-triage
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/collection_audit_triage_v1/inspect-%j.log
set -euo pipefail
export RECOVERY_BATCH=4
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/collection_audit_triage_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B inspect_failures.py
