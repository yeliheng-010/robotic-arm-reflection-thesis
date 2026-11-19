#!/bin/bash
#SBATCH --job-name=closure-reach-register
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_reachability_v1/prepare-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
/home/yeliheng/grasp_server/env_sim/bin/python -B -m qualified_closure_reachability_v1.register
