#!/bin/bash
#SBATCH --job-name=framework-analysis
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/home/yeliheng/grasp_server/framework_analysis_v1/audit-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/framework_ablation_v1/environment.sh
cd /home/yeliheng/grasp_server/framework_analysis_v1
/home/yeliheng/grasp_server/env_sim/bin/python -m unittest test_core -v
/home/yeliheng/grasp_server/env_sim/bin/python analyze.py
