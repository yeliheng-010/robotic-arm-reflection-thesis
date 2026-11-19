#!/bin/bash
set -euo pipefail
source /home/yeliheng/grasp_server/joint_representation_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/joint_policy_v1:/home/yeliheng/grasp_server/joint_representation_v1/physical:$PYTHONPATH
