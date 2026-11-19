#!/bin/bash
#SBATCH --job-name=checkpoint-failure-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_prompt_checkpoint_v1/failure-audit-v2-%j.log
set -euo pipefail
exec bash /home/yeliheng/grasp_server/qualified_prompt_checkpoint_v1/model.sh failure_audit_v2
