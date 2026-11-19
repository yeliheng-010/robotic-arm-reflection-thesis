#!/bin/bash
set -euo pipefail
cd /home/yeliheng/grasp_server/improvement_20261019/code
source training/server/qwen35_env.sh
export PYTHONPATH=/home/yeliheng/grasp_server/candidate_sft_v1:/home/yeliheng/grasp_server/stability_20261019:$PYTHONPATH
export TOKENIZERS_PARALLELISM=false
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
