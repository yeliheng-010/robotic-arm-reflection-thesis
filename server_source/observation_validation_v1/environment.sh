#!/bin/bash
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
cd /home/yeliheng/grasp_server/improvement_20261019/code
source training/server/qwen35_env.sh
source /home/yeliheng/grasp_server/refinement_v3/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/improvement_20261019/code:$PYTHONPATH
export PYTHONPATH=/home/yeliheng/grasp_server/observation_validation_v1:/home/yeliheng/grasp_server/framework_ablation_v1:/home/yeliheng/grasp_server/candidate_sft_v2:/home/yeliheng/grasp_server/scene_expansion_v1:/home/yeliheng/grasp_server/hard_cases_v1:/home/yeliheng/grasp_server/noisy_loop_v1:/home/yeliheng/grasp_server/route_loop_v1:/home/yeliheng/grasp_server/descent_route_v1:/home/yeliheng/grasp_server/descent_pose_v2:/home/yeliheng/grasp_server/feedback_semantics_v2:/home/yeliheng/grasp_server/recovery_study_v1:/home/yeliheng/grasp_server/bounded_reflection_v1:/home/yeliheng/grasp_server/refinement_next_v1:$PYTHONPATH
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
