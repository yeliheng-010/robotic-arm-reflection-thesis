#!/bin/bash
#SBATCH --job-name=visual-comparison-checks
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_comparison_v1/verify-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/visual_comparison_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_comparison_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B -m unittest discover -v
/home/yeliheng/grasp_server/qwen35/env/bin/python -B -c 'import prepare, run, report; print("imports passed; no model/physics/update")'
