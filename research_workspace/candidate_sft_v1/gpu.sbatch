#!/bin/bash
#SBATCH --job-name=candidate-sft-v1
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/candidate_sft_v1/gpu-%A_%a.log
set -euo pipefail
source /home/yeliheng/grasp_server/candidate_sft_v1/environment.sh
PY=/home/yeliheng/grasp_server/qwen35/env/bin/python
RUN=/home/yeliheng/grasp_server/candidate_sft_v1
case "$1" in
  smoke)
    "$PY" "$RUN/smoke.py" update
    "$PY" "$RUN/smoke.py" reload
    ;;
  train) "$PY" "$RUN/train.py" ;;
  before|after) "$PY" "$RUN/evaluate.py" "$1" --shard "$SLURM_ARRAY_TASK_ID" --shards 3 ;;
  *) exit 2 ;;
esac
