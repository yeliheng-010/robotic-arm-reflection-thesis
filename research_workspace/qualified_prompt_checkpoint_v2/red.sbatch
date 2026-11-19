#!/bin/bash
#SBATCH --job-name=checkpoint-recovery-red
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_prompt_checkpoint_v2/red-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest qualified_prompt_checkpoint_v2.test_provenance -v
