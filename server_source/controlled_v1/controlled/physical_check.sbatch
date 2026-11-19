#!/bin/bash
#SBATCH --job-name=controlled-physical-check
#SBATCH --partition=batch
#SBATCH --gres=gpu:v100:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --chdir=/home/yeliheng/grasp_server/improvement_20261019/code
#SBATCH --output=/home/yeliheng/grasp_server/controlled_v1/physical-check-%j.log
set -euo pipefail
source training/server/qwen35_env.sh
export PYTHONPATH=/home/yeliheng/grasp_server/controlled_v1:/home/yeliheng/grasp_server/diversity_v1:/home/yeliheng/grasp_server/flashnext_v1:/home/yeliheng/grasp_server/stability_20261019:/home/yeliheng/grasp_server/geometry_20261019:.
export MUJOCO_GL=egl MPLCONFIGDIR=/tmp/grasp-controlled PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
for case in 6 10; do
    for arm in retry rule; do
        /home/yeliheng/grasp_server/env_sim/bin/python -c "from controlled.worker import run; run($case, '$arm', run_name='physical_validation')"
    done
done
/home/yeliheng/grasp_server/env_sim/bin/python - <<'PY'
import json
from controlled.freeze import verify
from controlled.worker import ROOT
from controlled.config import tasks
from controlled.audit import audit_records, audit_feedback
from stability.collection_worker import verify_pair
from stability.collection_status import atomic

verify()
rows = []
for case in (6, 10):
    directory = ROOT/'physical_validation/tasks'/f'{case:02d}'
    results = {arm: json.loads((directory/arm/'result.json').read_text()) for arm in ('retry', 'rule')}
    for arm, result in results.items():
        audit_records(result, tasks()[case])
        calls = audit_feedback(directory/arm, result, arm=arm)
        rows.append(dict(case=case, arm=arm, calls=calls, success=result['success']))
    verify_pair(results['rule'], results['retry'])
assert any(row['calls'] for row in rows), 'Need real failure feedback in integration check'
atomic(ROOT/'physical_validation/verification.json', dict(passed=True, rows=rows, test_used=False))
print('Physical integration audit passed', rows, flush=True)
PY

