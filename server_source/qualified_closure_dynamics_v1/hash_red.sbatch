#!/bin/bash
#SBATCH --job-name=closure-hash-red
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_dynamics_v1/hash-red-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m unittest qualified_closure_dynamics_v1.test_hash -v
