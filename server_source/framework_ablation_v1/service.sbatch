#!/bin/bash
#SBATCH --job-name=framework-controller
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=08:00:00
#SBATCH --output=/home/yeliheng/grasp_server/framework_ablation_v1/controller-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/framework_ablation_v1/environment.sh
/home/yeliheng/grasp_server/env_sim/bin/python /home/yeliheng/grasp_server/framework_ablation_v1/orchestrator.py
