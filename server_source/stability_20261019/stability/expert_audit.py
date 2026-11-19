"""由原始规则/重试轨迹重建专家样本，独立于纯模型门禁。"""
import argparse
import hashlib
import json
from pathlib import Path
from stability.collection_status import atomic
from stability.collection_worker import verify_pair
from stability.dataset import digest
from stability.experiment import OUT
from stability.expert_config import configuration
from stability.expert_dataset import examples, SOURCE
from stability.expert_status import update


def read(path):
    return json.loads(path.read_text())


def validate_raw(expert, retry, summary):
    assert expert['method'] == 'reflection' and retry['method'] == 'retry'
    assert retry['reflector'] is None
    for result in (expert, retry):
        assert result['persistent_fault'] is True
        assert result['retry_protocol'] == 'restore_same_initial_scene_each_attempt'
        assert result['attempts'] == len(result['records'])
        assert result['success'] == any(r['accepted'] for r in result['records'])
        assert result['success'] or result['attempts'] == 3
        assert [r['attempt'] for r in result['records']] == list(range(1, result['attempts']+1))
    assert all('reflection' not in r and r['parameters'] == retry['records'][0]['parameters']
               for r in retry['records'])
    assert summary['paired'] is True
    assert summary['invalid'] == sum('reflection_error' in r for r in expert['records'])
    assert summary['calls'] == sum('reflection' in r or 'reflection_error' in r for r in expert['records'])


def validate_imports(directory):
    path = directory/'imports.json'
    if not path.exists():
        return
    imports = read(path)
    expected = {str(Path(read(p)[key]).resolve()) for p in (directory/'tasks').glob('*/summary.json')
                for key in ('expert_result', 'retry_result')}
    assert len(imports) == len(expected) and {item['copy'] for item in imports} == expected
    for item in imports:
        assert Path(item['copy']).resolve().is_relative_to(directory.resolve())
        assert all(hashlib.sha256(Path(item[key]).read_bytes()).hexdigest() == item['sha256']
                   for key in ('original', 'copy'))


def audit_task(directory, task):
    summary = read(directory/'summary.json')
    assert summary['task'] == task and summary['supervision_source'] == SOURCE
    paths = [Path(summary[k]).resolve() for k in ('expert_result', 'retry_result')]
    assert all(p.is_relative_to(directory.resolve()) for p in paths)
    expert, retry = map(read, paths)
    validate_raw(expert, retry, summary)
    verify_pair(expert, retry)
    assert expert['reflector'] == 'RuleReflector'
    assert all(r.get('reflection', {}).get('source', 'rule') == 'rule' for r in expert['records'])
    for result in (expert, retry):
        assert all(result[k] == v for k, v in task.items() if k != 'split')
        assert 1 <= len(result['records']) <= 3 and result['scene_jitter_m'] == .012
    rows = examples(expert, retry, task_id=directory.name, split=task['split'])
    assert digest(rows) == digest(summary['samples'])
    assert summary['expert_success'] == expert['success']
    assert summary['retry_success'] == retry['success']
    return len(rows)


def audit(directory):
    manifest = read(directory/'manifest.json')
    assert manifest == configuration(manifest['stage']), 'Frozen expert identity changed'
    summaries = sorted((directory/'tasks').glob('*/summary.json'))
    assert all(p.parent.name == f'{int(p.parent.name):05d}' and
               0 <= int(p.parent.name) < len(manifest['plan']) for p in summaries)
    validate_imports(directory)
    counts = [audit_task(path.parent, manifest['plan'][int(path.parent.name)]) for path in summaries]
    old_status = read(directory/'status.json') if (directory/'status.json').exists() else {}
    status = update(directory, planned=len(manifest['plan']), stage=manifest['stage'])
    status.update({k: old_status[k] for k in ('stop_reason', 'ended', 'worker_failures') if k in old_status})
    atomic(directory/'status.json', status)
    result = {'source_audit_passed': True, 'supervision_source': SOURCE,
        'audited_tasks': len(counts), 'raw_verified_samples': sum(counts), 'status': status,
        'manifest_sha256': digest(manifest), 'training_started': False,
        'code': manifest['code'], 'expert_code': manifest['expert_code'], 'generator': manifest['generator']}
    if manifest['stage'] == 'pilot':
        result['allow_batch'] = (len(counts) == len(manifest['plan']) == 12 and
            status['samples']['train'] >= 6 and status['invalid']/max(1, status['calls']) <= .2 and
            all(status['by_fault']['train'].get(f, 0) >= 1 for f in ('calibration', 'collision', 'placement')))
        atomic(OUT/'expert_gate.json', result)
    else:
        result['eligible_for_training_review'] = status['sample_count_gate'] and not status.get('worker_failures')
    atomic(directory/'audit.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    assert args.run.startswith('expert_') and '/' not in args.run
    result = audit(OUT/args.run)
    print(json.dumps({k: result[k] for k in ('source_audit_passed', 'audited_tasks',
        'raw_verified_samples', 'allow_batch', 'eligible_for_training_review') if k in result}), flush=True)


if __name__ == '__main__':
    main()
