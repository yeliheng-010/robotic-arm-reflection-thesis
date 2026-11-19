#!/bin/bash
#SBATCH --job-name=checkpoint-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_prompt_checkpoint_v1/audit-%j.log
set -euo pipefail
exec bash /home/yeliheng/grasp_server/qualified_prompt_checkpoint_v1/model.sh audit
