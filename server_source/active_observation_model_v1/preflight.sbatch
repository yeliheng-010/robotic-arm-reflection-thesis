#!/bin/bash
#SBATCH --job-name=active-preflight
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/active_observation_model_v1/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/active_observation_model_v1/environment.sh
cd /home/yeliheng/grasp_server/active_observation_model_v1
/home/yeliheng/grasp_server/env_sim/bin/python -m unittest discover -p 'test_*.py' -v
/home/yeliheng/grasp_server/env_sim/bin/python am_common.py
cd /tmp
/home/yeliheng/grasp_server/env_sim/bin/python -c 'from am_common import verify; print("FROZEN",len(verify()["scenes"]))'
