#!/bin/bash
#SBATCH --job-name=od-preflight
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/observation_decision_diagnostic_v1/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/observation_decision_diagnostic_v1/environment.sh
cd /home/yeliheng/grasp_server/observation_decision_diagnostic_v1
/home/yeliheng/grasp_server/env_sim/bin/python -m unittest discover -p 'test_*.py' -v
/home/yeliheng/grasp_server/env_sim/bin/python -c 'import ast,pathlib; [ast.parse(p.read_text()) for p in pathlib.Path(".").glob("*.py")]; print("Syntax checked")'
/home/yeliheng/grasp_server/env_sim/bin/python od_common.py
cd /tmp
/home/yeliheng/grasp_server/env_sim/bin/python -c 'from od_common import verify; print("FROZEN",len(verify()["cases"]))'
