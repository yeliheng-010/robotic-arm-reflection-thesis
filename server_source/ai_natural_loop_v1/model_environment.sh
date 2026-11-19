#!/bin/bash
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/candidate_sft_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/ai_natural_loop_v1:/home/yeliheng/grasp_server/ai_diagnosis_failure_v1:/home/yeliheng/grasp_server/ai_diagnosis_v1:$PYTHONPATH
exec /home/yeliheng/grasp_server/qwen35/env/bin/python -B /home/yeliheng/grasp_server/ai_natural_loop_v1/nc_service.py
