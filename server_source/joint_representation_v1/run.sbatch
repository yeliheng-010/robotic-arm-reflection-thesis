#!/bin/bash
#SBATCH --job-name=equivalent-angles-readonly
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/joint_representation_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/joint_representation_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/joint_representation_v1/test_angles.py
timeout 180 $SIM_PY -B /home/yeliheng/grasp_server/joint_representation_v1/jr_probe.py
timeout 180 $SIM_PY -B /home/yeliheng/grasp_server/joint_representation_v1/jr_full.py full
timeout 180 $SIM_PY -B /home/yeliheng/grasp_server/joint_representation_v1/jr_full.py audit
