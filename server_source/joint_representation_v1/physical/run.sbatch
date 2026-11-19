#!/bin/bash
#SBATCH --job-name=joint-equivalent-single-task
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:12:00
#SBATCH --output=/home/yeliheng/grasp_server/joint_representation_v1/physical/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/joint_representation_v1/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/joint_representation_v1/physical:$PYTHONPATH
cd /home/yeliheng/grasp_server/joint_representation_v1/physical
$SIM_PY -B test_runtime.py
$SIM_PY -B jp_worker.py prepare
timeout 180 $SIM_PY -B jp_worker.py preflight
timeout 300 $SIM_PY -B jp_worker.py execute
timeout 180 $SIM_PY -B jp_audit.py
