#!/bin/bash
#SBATCH --job-name=oriented-wiring-green-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:04:00
#SBATCH --output=/home/yeliheng/grasp_server/oriented_transfer_v1/physical_fix_v1/green-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/oriented_transfer_v1/physical/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/oriented_transfer_v1/physical_fix_v1:$PYTHONPATH
export CARRY_IMPL=fixed
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/physical_fix_v1/test_wiring.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/physical/test_commands.py
$SIM_PY -B /home/yeliheng/grasp_server/oriented_transfer_v1/physical_fix_v1/partial_audit.py
test -f /home/yeliheng/grasp_server/oriented_transfer_v1/physical_fix_v1/partial_audit.json
