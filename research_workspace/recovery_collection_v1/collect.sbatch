#!/bin/bash
#SBATCH --job-name=recovery-data-physical
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=08:00:00
#SBATCH --output=/home/yeliheng/grasp_server/recovery_collection_v1/collect-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/recovery_collection_v1/environment.sh
cd /home/yeliheng/grasp_server/recovery_collection_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_gate test_protocol -v
/home/yeliheng/grasp_server/env_sim/bin/python -B rc_prepare.py
/home/yeliheng/grasp_server/env_sim/bin/python -B rc_controller.py
/home/yeliheng/grasp_server/env_sim/bin/python -B rc_review.py
