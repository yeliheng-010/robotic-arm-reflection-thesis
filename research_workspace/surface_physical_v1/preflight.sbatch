#!/bin/bash
#SBATCH --job-name=surface-entry-preflight
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/surface_physical_v1/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/surface_physical_v1/environment.sh
$SIM_PY -B -m unittest surface_physical_v1.test_gate surface_physical_v1.test_wiring surface_physical_v1.test_held -v
$SIM_PY -B -m surface_physical_v1.worker prepare
timeout 180 $SIM_PY -B -m surface_physical_v1.worker preflight
timeout 180 $SIM_PY -B -m surface_physical_v1.audit preflight
