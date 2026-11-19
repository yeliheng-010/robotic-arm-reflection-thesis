#!/bin/bash
#SBATCH --job-name=qualified-native-audit
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:08:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_entry_v1/audit-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m unittest qualified_entry_v1.test_commands -v
timeout 450 $SIM_PY -B -m qualified_entry_v1.audit
