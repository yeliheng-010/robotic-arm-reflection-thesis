"""四分片每条件独立进程，异常停止且不覆盖证据。"""
import os
import subprocess
import sys
from pv_protocol import ROOT, SHARDS, verify


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    shard = int(os.environ['SLURM_ARRAY_TASK_ID'])
    for index in range(len(manifest['items'])):
        if index % SHARDS == shard:
            subprocess.run([sys.executable, str(ROOT/'pv_worker.py'), str(index)],
                           cwd=ROOT, check=True, timeout=900)


if __name__ == '__main__':
    main()
