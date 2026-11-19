#!/bin/bash
#SBATCH --job-name=recovery-physics-prepare
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/collection_scale_v1/physical-prepare-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/collection_scale_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B sc_physics.py prepare
