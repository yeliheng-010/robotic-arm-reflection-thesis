#!/bin/bash
#SBATCH --job-name=camera_joint_v1-register
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/camera_joint_v1/register-%A.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m unittest camera_joint_v1.test_policy camera_joint_v1.test_search pose_fresh_v1.test_pause pose_selective_v1.test_policy -v
$SIM_PY -B -c "import camera_joint_v1.worker; import camera_joint_v1.audit"
timeout 240 $SIM_PY -B -m camera_joint_v1.register
