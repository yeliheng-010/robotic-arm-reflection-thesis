#!/bin/bash
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/ai_safe_visual_loop_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/natural_span_guard_v1:/home/yeliheng/grasp_server/natural_grasp_span_audit_v1:$PYTHONPATH
