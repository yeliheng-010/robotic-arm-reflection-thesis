#!/bin/bash
#SBATCH --job-name=coverage-bounded-probes
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:12:00
#SBATCH --output=/home/yeliheng/grasp_server/coverage_repair_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/coverage_repair_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/test_proposals.py
$SIM_PY -B -c 'from reflection.__main__ import bootstrap; bootstrap(); from common import prepare; prepare()'
timeout 120 $SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/grasp_probe.py probe
timeout 120 $SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/grasp_probe.py audit
timeout 240 $SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/camera_probe.py probe
timeout 240 $SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/camera_probe.py audit
