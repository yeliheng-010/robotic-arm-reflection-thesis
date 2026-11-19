"""与纯教师pilot相同任务的规则机制基线，不导出训练样本。"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from stability.collection_plan import task_plan
from stability.collection_worker import verify_pair
from stability.experiment import OUT, THREADS, fingerprint, run


def configuration():
    return {'tasks': [{k: v for k, v in task.items() if k != 'split'} for task in task_plan('pilot')],
            'arms': ['stable'], 'fingerprint': fingerprint(), 'threads': THREADS,
            'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'source': 'rule', 'training_samples': 0}


def compare(directory, config):
    counts, teacher_counts = Counter(), Counter()
    for index, task in enumerate(config['tasks']):
        result = json.loads((directory/f'{index:02d}'/'stable/result.json').read_text())
        summary = json.loads((OUT/'pilot9_v1/tasks'/f'{index:05d}'/'summary.json').read_text())
        teacher = json.loads(Path(summary['teacher_result']).read_text())
        verify_pair(result, teacher)
        counts[task['fault']] += int(result['success'])
        teacher_counts[task['fault']] += int(teacher['success'])
    report = {'paired_tasks': len(config['tasks']), 'rule_success': dict(counts),
              'teacher_success': dict(teacher_counts), 'training_samples': 0}
    (directory/'verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    config, directory = configuration(), OUT/'rule_pilot_v1'
    assert all(os.environ.get(k) == v for k, v in THREADS.items())
    manifest = directory/'manifest.json'
    if parser.parse_args().freeze:
        directory.mkdir(exist_ok=True)
        with manifest.open('x') as stream:
            json.dump(config, stream, indent=2)
        return
    assert json.loads(manifest.read_text()) == config
    run(config, directory)
    compare(directory, config)


if __name__ == '__main__':
    main()

