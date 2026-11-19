#!/bin/bash
#SBATCH --job-name=checkpoint-recovery-prepare
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_prompt_checkpoint_v2/prepare-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest qualified_prompt_checkpoint_v2.test_provenance -v
/home/yeliheng/grasp_server/env_sim/bin/python -B -m qualified_prompt_checkpoint_v2.register
