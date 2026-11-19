#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/active_observation_model_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/container_layout_v2:/home/yeliheng/grasp_server/scene_expansion_v1:$PYTHONPATH
export PYTHONDONTWRITEBYTECODE=1
