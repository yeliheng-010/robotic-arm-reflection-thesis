#!/bin/bash
#SBATCH --job-name=pose-fresh-register
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/pose_fresh_v1/register-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m unittest pose_fresh_v1.test_policy pose_fresh_v1.test_evaluate pose_fresh_v1.test_pause pose_selective_v1.test_policy pose_replay_v1.test_runtime held_observation_v1.test_geometry -v
$SIM_PY -B -c 'import pose_fresh_v1.worker; import pose_fresh_v1.audit'
timeout 240 $SIM_PY -B -m pose_fresh_v1.register
