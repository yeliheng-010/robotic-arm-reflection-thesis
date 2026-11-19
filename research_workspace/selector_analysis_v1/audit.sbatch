#!/bin/bash
#SBATCH --job-name=selector-analysis
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/selector_analysis_v1/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/observation_model_control_v1/environment.sh
cd /home/yeliheng/grasp_server/selector_analysis_v1
/home/yeliheng/grasp_server/env_sim/bin/python -m unittest discover -p 'test_*.py' -v
/home/yeliheng/grasp_server/env_sim/bin/python analyze.py
