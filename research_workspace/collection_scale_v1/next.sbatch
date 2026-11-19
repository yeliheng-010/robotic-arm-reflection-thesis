#!/bin/bash
#SBATCH --job-name=recovery-next-batch-gate
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/collection_scale_v1/next-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/collection_scale_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_policy -v
/home/yeliheng/grasp_server/env_sim/bin/python -B sc_next.py
