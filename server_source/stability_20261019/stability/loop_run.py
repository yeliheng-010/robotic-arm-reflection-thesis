"""受Slurm管理的评估调度：模型服务与仿真共享本作业GPU。"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import subprocess
import time
import urllib.request
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.loop_freeze import ROOT, verify
from stability.loop_protocol import ARMS, PORT, WORKERS, summarize

SIM_PYTHON = '/home/yeliheng/grasp_server/env_sim/bin/python'
MODEL_PYTHON = '/home/yeliheng/grasp_server/qwen35/env/bin/python'


def wait_ready(process):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(180):
        assert process.poll() is None, 'Inference process exited'
        try:
            with opener.open(f'http://127.0.0.1:{PORT}/health', timeout=2) as response:
                if json.load(response)['ready']:
                    return
        except OSError:
            pass
        time.sleep(2)
    raise TimeoutError('Inference readiness timed out')


def execute(case, arm):
    log = ROOT/f'task_{case:02d}_{arm}.log'
    with log.open('x') as stream:
        subprocess.run([SIM_PYTHON, '-m', 'stability.loop_worker', '--case', str(case), '--arm', arm],
            stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=1800)
    return json.loads((ROOT/'tasks'/f'{case:02d}'/arm/'summary.json').read_text())


def collect(config):
    rows = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(execute, case, arm) for case in range(len(config['tasks'])) for arm in ARMS]
        for future in as_completed(futures):
            rows.append(future.result())
            verify()
            atomic(ROOT/'progress.json', dict(completed=len(rows), total=len(futures), metrics=summarize(rows)))
            print(json.dumps(rows[-1]), flush=True)
    return rows


def main():
    from stability.loop_audit import audit
    config = verify()
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'result.json').exists()
    atomic(ROOT/'runtime.json', dict(job=os.environ['SLURM_JOB_ID'],
        cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'), workers=WORKERS))
    with (ROOT/'service.log').open('x') as stream:
        process = subprocess.Popen([MODEL_PYTHON, '-m', 'stability.loop_service'], stdout=stream, stderr=subprocess.STDOUT)
        try:
            wait_ready(process)
            rows = collect(config)
            verification = audit(config, rows)
            atomic(ROOT/'result.json', dict(status='completed', metrics=summarize(rows),
                verification=verification, rows=rows, test_used=False))
        except BaseException as error:
            atomic(ROOT/'failure.json', {'error': repr(error)})
            raise
        finally:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    main()
