"""先核验预检和模型服务；任务失败保留分母，服务中断停止批量。"""
import argparse
import json
import os
import subprocess
import time
from stability.collection_status import atomic
from flashnext.client import ready
from flashnext.provenance import identity
from controlled.config import ARMS, tasks, scenario
from controlled.freeze import verify
from controlled.worker import ROOT, jsonlines
from controlled.metrics import summarize
from controlled.audit import audit_case

SIM_PYTHON = '/home/yeliheng/grasp_server/env_sim/bin/python'
SMOKE_CASE = 6
WORKER_TIMEOUT = 1800


def launch_checks(mode):
    verify()
    preflight = json.loads((ROOT/'preflight/result.json').read_text())
    assert preflight['passed'] and preflight['cases'] == len(tasks())
    for task, row in zip(tasks(), preflight['rows']):
        assert row['task'] == task and row['scenario'] == scenario(task['seed'], task['level'])
    if mode == 'pilot':
        smoke = json.loads((ROOT/'smoke/result.json').read_text())
        assert smoke['status'] == 'completed' and smoke['verification_passed']
        assert smoke['parsed_model_calls'] > 0 and smoke['service_errors'] == 0
    return ready()


def execute(root, case, arm):
    verify()
    if arm == 'flash':
        ready()
    with (root/f'task_{case:02d}_{arm}.log').open('x') as stream:
        subprocess.run([SIM_PYTHON, '-m', 'controlled.worker', '--case', str(case), '--arm', arm,
                        '--run', root.name], stdout=stream, stderr=subprocess.STDOUT,
                       check=True, timeout=WORKER_TIMEOUT)
    return json.loads((root/'tasks'/f'{case:02d}'/arm/'summary.json').read_text())


def write_report(root, result):
    lines = ['# 受控噪声开发实验', '', f"状态：{result['status']}；完成 {result['completed']}/{result['expected']} 次任务。",
             '', '|因素|方法|成功/任务|恢复/首次失败|无效输出|服务错误|', '|---|---|---|---|---|---|']
    for group, arms in summarize(result['rows']).items():
        for arm, metric in arms.items():
            if metric['tasks']:
                lines.append(f"|{group}|{arm}|{metric['successes']}/{metric['tasks']}|"
                             f"{metric['recoveries']}/{metric['first_failures']}|"
                             f"{metric['invalid_outputs']}|{metric['service_errors']}|")
    lines += ['', '全部为开发条件；未读取封存测试。反馈误差是模拟测量误差，错误类别和阶段仍是理想检测。',
              '任务失败保留在分母；服务故障与无效回答单独统计。此报告不声明统计显著性。']
    (root/'REPORT.md').write_text('\n'.join(lines)+'\n')


def run(mode):
    root = ROOT/mode
    try:
        models = launch_checks(mode)
    except Exception as error:
        atomic(ROOT/f'{mode}_launch.json', dict(status='blocked', error=repr(error), checked_at=time.time()))
        raise
    root.mkdir(exist_ok=False)
    model = identity()
    model['supervision'] = 'online development evaluation; no training labels supplied to model'
    atomic(root/'manifest.json', dict(models=models, model=model, job=os.environ['SLURM_JOB_ID'],
                                    cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES')))
    cases = [SMOKE_CASE] if mode == 'smoke' else list(range(len(tasks())))
    result = dict(status='running', expected=len(cases)*len(ARMS), completed=0, rows=[], audits=[],
                  test_used=False, started_at=time.time(), service_errors=0, parsed_model_calls=0)
    atomic(root/'progress.json', result)
    try:
        execute_cases(root, cases, result)
        verify()
        if mode == 'smoke':
            assert result['parsed_model_calls'] > 0, 'Smoke needs a real parsed reflection; review before batch'
        result.update(status='completed', verification_passed=True)
    except BaseException as error:
        result.update(status='failed', error=repr(error), verification_passed=False)
        raise
    finally:
        result['ended_at'] = time.time()
        result['metrics'] = summarize(result['rows'])
        atomic(root/'result.json', result)
        write_report(root, result)


def execute_cases(root, cases, result):
    for case in cases:
        for arm in ARMS:
            row = execute(root, case, arm)
            result['rows'].append(row)
            result['completed'] = len(result['rows'])
            result['service_errors'] += row['service_errors']
            if arm == 'flash':
                events = jsonlines(root/'tasks'/f'{case:02d}'/arm/'requests.jsonl')
                result['parsed_model_calls'] += sum('parsed' in e for e in events)
            atomic(root/'progress.json', result)
            print(json.dumps(row), flush=True)
            if row['service_errors']:
                raise RuntimeError('Model service interrupted; preserve completed runs and stop batch')
        result['audits'].append(audit_case(root, case, tasks()[case]))
        atomic(root/'audits.json', result['audits'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=('smoke', 'pilot'), required=True)
    args = parser.parse_args()
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm for simulation'
    run(args.mode)
