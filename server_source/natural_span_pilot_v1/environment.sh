#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/natural_qualified_pilot_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/natural_span_pilot_v1:/home/yeliheng/grasp_server/natural_span_guard_v1:/home/yeliheng/grasp_server/natural_grasp_span_audit_v1:$PYTHONPATH
