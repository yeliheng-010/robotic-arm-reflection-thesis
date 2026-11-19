#!/bin/bash
#SBATCH --job-name=set-loop-preflight
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/set_closed_loop_v2/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/set_closed_loop_v2/environment.sh
cd /home/yeliheng/grasp_server/set_closed_loop_v2
/home/yeliheng/grasp_server/env_sim/bin/python -m unittest test_adapters test_boundaries test_stopping test_reuse test_paths -v
/home/yeliheng/grasp_server/env_sim/bin/python freeze.py
/home/yeliheng/grasp_server/env_sim/bin/python -c 'from common import verify; m=verify(); print("FROZEN_VERIFIED",len(m["entries"]))'
cd /tmp
/home/yeliheng/grasp_server/env_sim/bin/python -c 'from common import verify; print("CWD_INDEPENDENT",len(verify()["entries"]))'
