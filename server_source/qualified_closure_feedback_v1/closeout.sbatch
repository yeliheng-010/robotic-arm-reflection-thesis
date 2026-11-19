#!/bin/bash
#SBATCH --job-name=closure-feedback-closeout
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_feedback_v1/closeout-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m qualified_closure_feedback_v1.closeout
