"""独立子进程，按固定清单完成24个增强条件。"""
import os
import subprocess
import sys
from sf_common import ROOT, SHARDS, enhanced, verify


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    items = enhanced(verify())
    shard = int(os.environ['SLURM_ARRAY_TASK_ID'])
    for index in range(len(items)):
        if index % SHARDS == shard:
            subprocess.run([sys.executable, str(ROOT/'sf_worker.py'), str(index)],
                           cwd=ROOT, check=True, timeout=900)


if __name__ == '__main__':
    main()
