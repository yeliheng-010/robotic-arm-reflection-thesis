#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/natural_qualified_pilot_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/ai_safe_visual_loop_v1:/home/yeliheng/grasp_server/ai_visual_service_v1:/home/yeliheng/grasp_server/ai_multimodal_requests_v1:/home/yeliheng/grasp_server/ai_tracking_facts_v1:/home/yeliheng/grasp_server/ai_observable_facts_v1:$PYTHONPATH
