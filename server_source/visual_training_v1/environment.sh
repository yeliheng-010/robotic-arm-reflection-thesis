#!/bin/bash
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
source /home/yeliheng/grasp_server/candidate_sft_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/visual_training_v1:/home/yeliheng/grasp_server/visual_sft_v1:/home/yeliheng/grasp_server/ai_visual_input_v1/torchvision_overlay:$PYTHONPATH
