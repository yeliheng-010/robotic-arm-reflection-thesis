#!/bin/bash
#SBATCH --job-name=sd-test
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --gres=gpu:1
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/scene_diversity_v2/test-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/scene_diversity_v2/environment.sh
cd /home/yeliheng/grasp_server/scene_diversity_v2
$SIM_PY -m unittest discover -s . -p 'test_*.py' -v
