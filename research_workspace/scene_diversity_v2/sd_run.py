"""每个条件独立子进程，超时/工程错误中止，不静默重跑。"""
import os
import subprocess
import sys
from sd_config import ROOT
from sd_common import verify, read


def main(phase):
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    render = read(ROOT/'render_verification.json')
    assert render['passed'] and render['complete'] and render['accounted']==36
    if phase=='batch':
        gate = read(ROOT/'smoke_verification.json')
        assert gate['passed'] and gate['complete'] and gate['accounted']==12
    indices = range(12) if phase=='smoke' else range(12, len(manifest['items']))
    shard = int(os.environ['SLURM_ARRAY_TASK_ID'])
    for index in indices:
        if index % 4 != shard:
            continue
        subprocess.run([sys.executable, str(ROOT/'sd_physics.py'), str(index)],
                       check=True, timeout=900, cwd=ROOT)


if __name__ == '__main__':
    main(sys.argv[1])
