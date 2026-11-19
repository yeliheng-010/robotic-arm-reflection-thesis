#!/bin/bash
#SBATCH --job-name=checkpoint-static-prepare
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_checkpoint_preflight_v1/prepare-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest qualified_checkpoint_preflight_v1.test_protocol -v
/home/yeliheng/grasp_server/env_sim/bin/python -B -m qualified_checkpoint_preflight_v1.register
