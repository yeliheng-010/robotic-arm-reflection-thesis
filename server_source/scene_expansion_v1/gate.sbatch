#!/bin/bash
#SBATCH --job-name=expand-gate
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/scene_expansion_v1/gate-%j.log
set -euo pipefail
source training/server/qwen35_env.sh
source /home/yeliheng/grasp_server/refinement_v3/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/scene_expansion_v1:/home/yeliheng/grasp_server/noisy_loop_v1:/home/yeliheng/grasp_server/route_loop_v1:/home/yeliheng/grasp_server/descent_route_v1:/home/yeliheng/grasp_server/descent_pose_v2:/home/yeliheng/grasp_server/feedback_semantics_v2:/home/yeliheng/grasp_server/recovery_study_v1:/home/yeliheng/grasp_server/bounded_reflection_v1:/home/yeliheng/grasp_server/refinement_next_v1:$PYTHONPATH
/home/yeliheng/grasp_server/env_sim/bin/python -m expand.gate "$1"
