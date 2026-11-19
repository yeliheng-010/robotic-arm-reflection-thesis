#!/bin/bash
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/ai_diagnosis_failure_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/ai_natural_loop_v1:$PYTHONPATH
