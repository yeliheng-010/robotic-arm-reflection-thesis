"""每组任务使用独立解释器，退出时由操作系统释放原生仿真内存。"""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from stability.collection_status import atomic

TASK_TIMEOUT_SECONDS = 1800


def execute_isolated(task, root):
    directory = Path(root)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = time.time_ns()
    with (directory/f'process_{stamp}.log').open('w') as stream:
        subprocess.run([sys.executable, '-m', 'stability.recovery_task', '--root', str(directory)],
            input=json.dumps(task), text=True, stdout=stream, stderr=subprocess.STDOUT,
            check=True, timeout=TASK_TIMEOUT_SECONDS)
    return json.loads((directory/'summary.json').read_text())


def main():
    from stability.expert_worker import execute
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    task, started = json.load(sys.stdin), time.monotonic()
    execute(task, str(args.root))
    atomic(args.root/f'process_{os.getpid()}_metrics.json', {
        'pid': os.getpid(), 'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'elapsed_s': time.monotonic()-started, 'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'),
        'process_policy': 'one_task_per_fresh_interpreter'})


if __name__ == '__main__':
    main()
