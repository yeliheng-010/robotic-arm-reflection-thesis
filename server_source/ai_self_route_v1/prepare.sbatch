#!/bin/bash
#SBATCH --job-name=self-route-prepare
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_self_route_v1/prepare-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/ai_self_route_v1/environment.sh
cd /home/yeliheng/grasp_server/ai_self_route_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B sr_prepare.py
