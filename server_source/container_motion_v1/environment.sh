#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/container_recovery_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/container_motion_v1:/home/yeliheng/grasp_server/container_decision_diagnostic_v1:$PYTHONPATH
