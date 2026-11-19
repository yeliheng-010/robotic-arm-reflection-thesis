#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/container_motion_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/scene_diversity_v2:$PYTHONPATH
export SIM_PY=/home/yeliheng/grasp_server/env_sim/bin/python
export PYTHONDONTWRITEBYTECODE=1
