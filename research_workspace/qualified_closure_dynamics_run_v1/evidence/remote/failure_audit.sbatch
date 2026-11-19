#!/bin/bash
#SBATCH --job-name=closure-failure-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --no-requeue
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_dynamics_run_v1/failure-audit-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m qualified_closure_dynamics_run_v1.failure_audit
