#!/bin/bash
#SBATCH --job-name=checkpoint-model
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_prompt_checkpoint_v1/run-%j.log
set -euo pipefail
exec bash /home/yeliheng/grasp_server/qualified_prompt_checkpoint_v1/model.sh model
