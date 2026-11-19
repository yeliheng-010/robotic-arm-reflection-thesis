#!/bin/bash
#SBATCH --job-name=recovery-qualification-path-v2
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=06:00:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_collection_v1/qualification-v2-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_collection_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B qualification_resume_v2.py
