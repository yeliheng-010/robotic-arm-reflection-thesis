#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/scene_diversity_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/camera_visibility_v3:/home/yeliheng/grasp_server/scene_pair_feasibility_v1:$PYTHONPATH
export PYTHONDONTWRITEBYTECODE=1
