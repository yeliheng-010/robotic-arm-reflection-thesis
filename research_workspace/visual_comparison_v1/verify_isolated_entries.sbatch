#!/bin/bash
#SBATCH --job-name=visual-comparison-isolated-imports
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=12G
#SBATCH --time=00:10:00
#SBATCH --output=/home/yeliheng/grasp_server/visual_comparison_v1/isolated-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/visual_comparison_v1/environment.sh
cd /home/yeliheng/grasp_server/visual_comparison_v1
/home/yeliheng/grasp_server/qwen35/env/bin/python -B - <<'PY'
import os
import subprocess
import sys
from pathlib import Path

root = Path.cwd()
assert os.environ.get('SLURM_JOB_ID')
for name in ('prepare', 'run', 'report'):
    code = (
        f'import {name} as entry; from pathlib import Path; '
        f'assert Path(entry.__file__).resolve() == Path({str(root / (name + ".py"))!r}); '
        'print(entry.__file__)'
    )
    if name in ('run', 'report'):
        code += (
            '; import prepare; '
            f'assert Path(prepare.__file__).resolve() == Path({str(root / "prepare.py")!r}); '
            'assert entry.lines is prepare.lines'
        )
    subprocess.run([sys.executable, '-B', '-c', code], cwd=root, check=True)
print('All three actual process entries verified; zero model load/generation/update')
PY
