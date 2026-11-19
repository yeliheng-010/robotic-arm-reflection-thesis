#!/bin/bash
#SBATCH --job-name=pair-recovery
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:12:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_pair_v2/anchor-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_pair_v2/environment.sh
cd /home/yeliheng/grasp_server/scene_pair_v2
$SIM_PY -m unittest discover -s . -p 'test_*.py' -v
$SIM_PY pair_run.py --scene baseline --seed 960102 --output anchor/baseline
$SIM_PY pair_run.py --scene varied_noisy --seed 960102 --output anchor/varied_noisy
