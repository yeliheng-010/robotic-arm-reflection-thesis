#!/bin/bash
#SBATCH --job-name=recovery-next-batch-prepare
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/collection_scale_v1/prepare-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/collection_scale_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B sc_qualification.py prepare
