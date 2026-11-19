#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/ai_route_bridge_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/ai_self_route_v1:/home/yeliheng/grasp_server/natural_self_guard_v1:/home/yeliheng/grasp_server/scene_pair_contact_diagnostic_v1:$PYTHONPATH
