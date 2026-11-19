#!/bin/bash
#SBATCH --job-name=recovery-data-qualification
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=06:00:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_collection_v1/qualification-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_collection_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B rc_qualification.py
