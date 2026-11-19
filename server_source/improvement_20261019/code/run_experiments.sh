#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
if [[ -n "${GRASP_PYTHON:-}" ]]; then
    EXPERIMENT_PYTHON="$GRASP_PYTHON"
elif [[ "${CONDA_DEFAULT_ENV:-}" == "graspnet" ]]; then
    EXPERIMENT_PYTHON="$(command -v python)"
elif [[ -x /home/yeliheng/miniconda3/envs/graspnet/bin/python ]]; then
    EXPERIMENT_PYTHON=/home/yeliheng/miniconda3/envs/graspnet/bin/python
else
    EXPERIMENT_PYTHON="$(command -v python3)"
fi
export MUJOCO_GL=egl
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/grasp-reflection-matplotlib}"
export REFLECTION_LLM_CACHE=0
exec "$EXPERIMENT_PYTHON" -u -m experiments.run_suite "$@"
