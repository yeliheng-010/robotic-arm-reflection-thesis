#!/bin/bash
#SBATCH --job-name=framework-preflight
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/framework_ablation_v1/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/framework_ablation_v1/environment.sh
cd /home/yeliheng/grasp_server/framework_ablation_v1
/home/yeliheng/grasp_server/env_sim/bin/python -m unittest discover -p 'test_*.py' -v
/home/yeliheng/grasp_server/env_sim/bin/python freeze.py
cd /tmp
/home/yeliheng/grasp_server/env_sim/bin/python -c 'from common import verify; print("CWD_INDEPENDENT",len(verify()["entries"]))'
