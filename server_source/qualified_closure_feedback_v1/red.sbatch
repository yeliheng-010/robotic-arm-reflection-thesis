#!/bin/bash
#SBATCH --job-name=closure-feedback-red
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_feedback_v1/red-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest qualified_closure_feedback_v1.test_policy -v
