#!/usr/bin/env bash
set -euo pipefail
TRAIN_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export CONDA_PKGS_DIRS="$TRAIN_ROOT/conda_pkgs"
export PIP_DISABLE_PIP_VERSION_CHECK=1
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4
export PYTHONUNBUFFERED=1

write_status() {
    python3 -c 'import json,sys,time; from pathlib import Path; p=Path(sys.argv[1]); q=p.with_suffix(".tmp"); q.write_text(json.dumps({"phase":sys.argv[2],"updated_at":time.time()})); q.replace(p)' \
        "$TRAIN_ROOT/setup_status.json" "$1"
}
trap 'write_status failed' ERR
write_status creating_python
if [[ ! -x "$TRAIN_ROOT/env/bin/python" ]]; then
    /opt/anaconda3/bin/conda create --yes --prefix "$TRAIN_ROOT/env" \
        --override-channels --channel conda-forge --solver libmamba \
        --repodata-fn current_repodata.json python=3.11 pip
fi
PY="$TRAIN_ROOT/env/bin/python"
write_status installing_pytorch
"$PY" -m pip install --retries 3 --timeout 60 \
    torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121
write_status installing_training_dependencies
"$PY" -m pip install --retries 3 --timeout 60 -r "$TRAIN_ROOT/requirements.txt"
"$PY" -m pip check
"$PY" -c 'import torch,transformers,peft,accelerate,bitsandbytes; print("Training imports OK",torch.__version__,transformers.__version__,peft.__version__)'
write_status ready
