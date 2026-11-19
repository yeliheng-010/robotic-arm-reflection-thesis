#!/bin/bash
#SBATCH --job-name=set-sft-audit
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/set_sft_v1/cpu-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/set_sft_v1/environment.sh
PY=/home/yeliheng/grasp_server/qwen35/env/bin/python
RUN=/home/yeliheng/grasp_server/set_sft_v1
case "$1" in
  preflight)
    "$PY" -m unittest discover -s "$RUN" -p 'test_*.py'
    "$PY" "$RUN/set_data.py"
    ;;
  freeze) "$PY" "$RUN/set_freeze.py" ;;
  audit) "$PY" "$RUN/set_audit.py" ;;
  *) exit 2 ;;
esac
