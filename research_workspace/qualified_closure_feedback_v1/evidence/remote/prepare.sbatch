#!/bin/bash
#SBATCH --job-name=closure-feedback-prepare
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_feedback_v1/prepare-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
SIM_PY=/home/yeliheng/grasp_server/env_sim/bin/python
$SIM_PY -B -m unittest qualified_closure_feedback_v1.test_policy qualified_joint_feedback_v1.test_policy qualified_closure_v1.test_policy qualified_closure_v1.test_adapter -v
$SIM_PY -B -m qualified_closure_feedback_v1.register
