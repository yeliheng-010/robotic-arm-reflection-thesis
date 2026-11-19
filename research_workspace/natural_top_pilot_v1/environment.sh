#!/bin/bash
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/natural_span_pilot_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/natural_top_pilot_v1:/home/yeliheng/grasp_server/observed_top_pose_v1:$PYTHONPATH
