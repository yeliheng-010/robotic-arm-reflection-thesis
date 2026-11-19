#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/active_observation_model_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/observation_decision_diagnostic_v2:$PYTHONPATH
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false
