#!/usr/bin/env bash
# Shared libraries are read only; Python packages remain isolated in the Qwen3.5 venv.
export LD_LIBRARY_PATH="/home/yeliheng/grasp_qlora/env/lib/python3.11/site-packages/nvidia/cudnn/lib:/home/yeliheng/grasp_qlora/env/lib/python3.11/site-packages/nvidia/nccl/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
