#!/bin/bash
#SBATCH --job-name=sensor-independent-register
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/sensor_independent_v1/register-%A.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
$SIM_PY -B -m unittest sensor_independent_v1.test_resources sensor_independent_v1.test_assessment pose_fresh_v1.test_pause camera_joint_v1.test_policy depth_diagnostic_v1.test_numeric -v
$SIM_PY -B -c "import sensor_independent_v1.worker; import sensor_independent_v1.audit"
timeout 240 $SIM_PY -B -m sensor_independent_v1.register
