#!/bin/bash
#SBATCH --job-name=observable-facts-test
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_observable_facts_v1/test-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server/ai_observable_facts_v1
/home/yeliheng/grasp_server/env_sim/bin/python -B -m unittest test_public_execution -v
