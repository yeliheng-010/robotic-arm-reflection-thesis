#!/bin/bash
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/camera_collection_v1:/home/yeliheng/grasp_server/recovery_integrity_v3:/home/yeliheng/grasp_server/recovery_integrity_v2:$PYTHONPATH:/home/yeliheng/grasp_server/camera_visibility_v6:/home/yeliheng/grasp_server/scene_pair_feasibility_v1
export SIM_PY=/home/yeliheng/grasp_server/env_sim/bin/python
export PYTHONDONTWRITEBYTECODE=1
