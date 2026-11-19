#!/bin/bash
#SBATCH --job-name=recovery-data-tests
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_collection_v1/verify-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_collection_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_gate test_protocol -v
