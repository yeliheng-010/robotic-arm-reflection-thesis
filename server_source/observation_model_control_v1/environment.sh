#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/observation_validation_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/observation_model_control_v1:$PYTHONPATH
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false
