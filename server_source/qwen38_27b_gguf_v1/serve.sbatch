#!/bin/bash
#SBATCH --job-name=qwen38_27b_api
#SBATCH --partition=batch
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/qwen38_27b_gguf_v1/serve-%j.log
set -euo pipefail
ROOT=/home/yeliheng/grasp_server/qwen38_27b_gguf_v1
PY=/home/yeliheng/grasp_server/qwen35/env/bin/python
test -s "$ROOT/ready.txt"
test -s "$ROOT/model-ready.txt"
"$PY" -c 'import socket; s=socket.socket(); assert s.connect_ex(("127.0.0.1",38271)) != 0, "Port is occupied"; s.close()'
printf 'job=%s CUDA_VISIBLE_DEVICES=%s\n' "$SLURM_JOB_ID" "$CUDA_VISIBLE_DEVICES"
"$ROOT/build/bin/llama-server" \
  --model "$ROOT/models/Qwen3.8-27B-UD-Q4_K_M.gguf" \
  --alias qwen3.8-27b-q4 --host 127.0.0.1 --port 38271 \
  --n-gpu-layers 99 --split-mode layer --tensor-split 1,1 \
  --ctx-size 4096 --parallel 1 --batch-size 512 --ubatch-size 128 \
  --threads 8 --threads-batch 8 --flash-attn off \
  --cache-type-k f16 --cache-type-v f16 \
  --jinja --chat-template-kwargs '{"enable_thinking":false}' \
  > "$ROOT/engine-$SLURM_JOB_ID.log" 2>&1 &
ENGINE_PID=$!
trap 'kill "$ENGINE_PID" 2>/dev/null || true' EXIT
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/home/yeliheng/grasp_server/stability_20261019:/home/yeliheng/grasp_server/geometry_20261019:.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 MKL_NUM_THREADS=1
"$PY" "$ROOT/smoke.py"
wait "$ENGINE_PID"

