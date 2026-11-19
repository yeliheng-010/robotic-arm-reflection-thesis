"""独立恢复审计；保留冻结的原专家审计代码。"""
from pathlib import Path
from reflection.errors import ErrorReport, ErrorType
from reflection.reflector import Parameters, RuleReflector
from stability.collection_status import atomic
from stability.collection_worker import verify_pair
from stability.dataset import digest
from stability.expert_audit import audit_task, read, validate_imports
from stability.expert_config import configuration
from stability.expert_dataset import examples, replay, SOURCE
from stability.expert_status import update


def verify_record_counts(result, *, early=False):
    records = result['records']
    assert result['persistent_fault'] is True
    assert result['retry_protocol'] == 'restore_same_initial_scene_each_attempt'
    assert result['attempts'] == len(records) and 1 <= len(records) <= 3
    assert result['success'] == any(r['accepted'] for r in records)
    assert result['success'] or len(records) == 3 or early
    assert [r['attempt'] for r in records] == list(range(1, len(records)+1))


def replay_invalid(record, history):
    raw = record['error']
    report = ErrorReport(ErrorType(raw['error_type']), raw['message'], raw['evidence'],
                         detector=raw['detector'])
    try:
        RuleReflector().reflect(report, Parameters().updated(record['parameters']), history)
    except ValueError as error:
        assert str(error) == record['reflection_error'], 'Invalid correction reason differs'
        return
    raise AssertionError('Recorded reflection error cannot be reproduced')


def validate_early_exit(expert, retry, summary):
    assert expert['method'] == 'reflection' and expert['reflector'] == 'RuleReflector'
    assert retry['method'] == 'retry' and retry['reflector'] is None
    assert expert['success'] is False and 1 <= expert['attempts'] < 3
    assert summary['samples'] == [] and summary['paired'] is True
    verify_record_counts(expert, early=True)
    verify_record_counts(retry)
    assert all('reflection' not in r and 'reflection_error' not in r and
               r['parameters'] == retry['records'][0]['parameters'] for r in retry['records'])
    records, history = expert['records'], []
    assert summary['invalid'] == 1 and summary['calls'] == len(records)
    for record in records[:-1]:
        assert 'reflection_error' not in record and 'reflection' in record
        answer = replay(record, history)
        history.append({'error': record['error'], 'reflection': answer})
    assert 'reflection' not in records[-1] and 'reflection_error' in records[-1]
    replay_invalid(records[-1], history)


def audit_recovered_task(directory, task):
    summary = read(directory/'summary.json')
    paths = [Path(summary[k]).resolve() for k in ('expert_result', 'retry_result')]
    assert all(p.is_relative_to(directory.resolve()) for p in paths)
    expert, retry = map(read, paths)
    if expert['success'] or expert['attempts'] == 3:
        return audit_task(directory, task), False
    assert summary['task'] == task and summary['supervision_source'] == SOURCE
    validate_early_exit(expert, retry, summary)
    verify_pair(expert, retry)
    for result in (expert, retry):
        assert all(result[k] == v for k, v in task.items() if k != 'split')
        assert result['scene_jitter_m'] == .012
    rows = examples(expert, retry, task_id=directory.name, split=task['split'])
    assert rows == summary['samples'] == []
    assert summary['expert_success'] == expert['success']
    assert summary['retry_success'] == retry['success']
    return 0, True


def audit(directory):
    manifest = read(directory/'manifest.json')
    assert manifest == configuration(manifest['stage']), 'Frozen expert identity changed'
    validate_imports(directory)
    counts, early = [], []
    for path in sorted((directory/'tasks').glob('*/summary.json')):
        name = path.parent.name
        assert name == f'{int(name):05d}' and 0 <= int(name) < len(manifest['plan'])
        count, aborted = audit_recovered_task(path.parent, manifest['plan'][int(name)])
        counts.append(count)
        if aborted:
            early.append(name)
    old = read(directory/'status.json') if (directory/'status.json').exists() else {}
    status = update(directory, planned=len(manifest['plan']), stage=manifest['stage'])
    status.update({k: old[k] for k in ('stop_reason', 'ended', 'worker_failures', 'job',
                                      'orchestration', 'recovery_record') if k in old})
    atomic(directory/'status.json', status)
    result = dict(source_audit_passed=True, supervision_source=SOURCE, audited_tasks=len(counts),
        raw_verified_samples=sum(counts), verified_early_aborts_without_samples=early,
        status=status, manifest_sha256=digest(manifest), audit_version='recovery_v1',
        eligible_for_training_review=status['sample_count_gate'] and not status.get('worker_failures'))
    atomic(directory/'recovery_audit.json', result)
    return result
