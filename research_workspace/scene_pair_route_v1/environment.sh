#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_candidates_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/scene_pair_route_v1:/home/yeliheng/grasp_server/scene_pair_guard_v2:/home/yeliheng/grasp_server/scene_pair_guard_v1:/home/yeliheng/grasp_server/scene_pair_contact_diagnostic_v1:$PYTHONPATH
