#!/bin/bash
#SBATCH --job-name=pose-replay-v1
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/pose_replay_v1/run-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m unittest pose_replay_v1.test_runtime held_observation_v1.test_geometry -v
timeout 420 $SIM_PY -B -m pose_replay_v1.worker
timeout 30 $SIM_PY -B -m pose_replay_v1.evaluate
timeout 90 $SIM_PY -B -m pose_replay_v1.audit
