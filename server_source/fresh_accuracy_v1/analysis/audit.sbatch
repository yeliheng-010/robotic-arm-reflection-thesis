#!/bin/bash
#SBATCH --job-name=fresh-coverage-audit
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/fresh_accuracy_v1/analysis/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/fresh_accuracy_v1/environment.sh
$SIM_PY -B /home/yeliheng/grasp_server/fresh_accuracy_v1/analysis/audit_coverage.py
