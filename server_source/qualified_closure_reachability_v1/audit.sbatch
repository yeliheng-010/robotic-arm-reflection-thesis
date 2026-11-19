#!/bin/bash
#SBATCH --job-name=closure-reach-audit
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/qualified_closure_reachability_v1/audit-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server
/home/yeliheng/grasp_server/env_sim/bin/python -B -m qualified_closure_reachability_v1.audit
