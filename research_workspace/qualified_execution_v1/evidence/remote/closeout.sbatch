#!/bin/bash
#SBATCH --job-name=qualified-exec-closeout
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_execution_v1/closeout-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
export PYTHONPATH=/home/yeliheng/grasp_server${PYTHONPATH:+:$PYTHONPATH}
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
SIM_PY=/home/yeliheng/grasp_server/env_sim/bin/python
$SIM_PY -B -m unittest qualified_execution_v1.test_policy qualified_execution_v1.test_guards qualified_entry_v1.test_commands
$SIM_PY -B -m qualified_execution_v1.closeout
