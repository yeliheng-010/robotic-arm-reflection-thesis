#!/bin/bash
#SBATCH --job-name=scene-pair
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_v1/verify-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_v1/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_v1
$SIM_PY -m unittest discover -s . -p 'test_*.py' -v
$SIM_PY pair_run.py --scene baseline --output smoke/baseline
$SIM_PY pair_run.py --scene varied_noisy --output smoke/varied_noisy
