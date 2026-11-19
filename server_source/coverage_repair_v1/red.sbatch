#!/bin/bash
#SBATCH --job-name=coverage-bounded-proposals-red
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:02:00
#SBATCH --output=/home/yeliheng/grasp_server/coverage_repair_v1/red-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/coverage_repair_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/coverage_repair_v1/test_proposals.py
