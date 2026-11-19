#!/bin/bash
#SBATCH --job-name=bounded-model-action-space
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/action_space_audit_v1/run-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/model_grasp_gpu_v1/environment.sh
$SIM_PY -B -m unittest action_space_audit_v1.test_catalogue action_space_audit_v1.test_cache -v
$SIM_PY -B -m action_space_audit_v1.register
$SIM_PY -B -m action_space_audit_v1.endpoints probe
$SIM_PY -B -m action_space_audit_v1.endpoints audit
$SIM_PY -B -m action_space_audit_v1.paths probe
$SIM_PY -B -m action_space_audit_v1.paths audit
