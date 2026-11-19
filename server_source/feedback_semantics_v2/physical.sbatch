#!/bin/bash
#SBATCH --job-name=semantic-contact-diagnostic
#SBATCH --partition=batch
#SBATCH --gres=gpu:v100:1
#SBATCH --array=0-1%2
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/feedback_semantics_v2/physical-%A_%a.log
set -euo pipefail
source training/server/qwen35_env.sh
source /home/yeliheng/grasp_server/refinement_v3/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/feedback_semantics_v2:/home/yeliheng/grasp_server/recovery_study_v1:/home/yeliheng/grasp_server/bounded_reflection_v1:/home/yeliheng/grasp_server/refinement_next_v1:$PYTHONPATH
/home/yeliheng/grasp_server/env_sim/bin/python -m semanticfix2.run --phase "$1" --shard "$SLURM_ARRAY_TASK_ID"
