#!/bin/bash
#SBATCH --job-name=grasp-batch-summary
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:03:00
#SBATCH --no-requeue
#SBATCH --output=/home/yeliheng/grasp_server/qualified_grasp_batch_v1/summary-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
python3 -B -m qualified_grasp_batch_v1.summarize
