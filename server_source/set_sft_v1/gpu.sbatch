#!/bin/bash
#SBATCH --job-name=set-sft-4b
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=/home/yeliheng/grasp_server/set_sft_v1/gpu-%A_%a.log
set -euo pipefail
source /home/yeliheng/grasp_server/set_sft_v1/environment.sh
PY=/home/yeliheng/grasp_server/qwen35/env/bin/python
RUN=/home/yeliheng/grasp_server/set_sft_v1
case "$1" in
  smoke)
    "$PY" "$RUN/set_smoke.py" update
    "$PY" "$RUN/set_smoke.py" reload
    ;;
  train) "$PY" "$RUN/set_train.py" ;;
  before|after) "$PY" "$RUN/set_eval.py" "$1" --shard "$SLURM_ARRAY_TASK_ID" ;;
  *) exit 2 ;;
esac
