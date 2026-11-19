"""独立后处理进程读取私有实测后果；不把它们发送给模型。"""
from ac_common import common, TRAINING, locations, lines, classify
from pair_metrics import compare_pairs
from sv_strategy_actions import validate


def classify_response(item, *, folder, request, facts):
    path = folder / item['input_id'] / 'response.json'
    assert common.sha(path) == item['response_sha256']
    response = common.read(path)
    assert response['identity']['adapter_enabled'] is True
    assert response['identity']['manifest_sha256'] == common.sha(TRAINING / 'manifest.json')
    parsed = validate(response, request, mode='direct')
    assert parsed == item['validation']
    action = parsed['parsed']['action'] if parsed['valid'] else None
    return dict(input_id=item['input_id'], snapshot_id=facts['snapshot_id'],
        completed=facts['completed'], model=classify(action, facts['outcomes'],
            valid=parsed['valid'], completed=facts['completed']))


def main():
    common.job('SLURM_JOB_ID')
    prepared, base = locations()
    manifest = common.verify(prepared / 'manifest.json')
    common.verify(base / 'manifest.json')
    base_report = common.verify(base / 'report.json')
    folder = prepared / 'adapter_comparison'
    complete = common.read(folder / 'complete.json')
    assert complete['passed'] and complete['manifest_sha256'] == common.sha(prepared / 'manifest.json')
    assert complete['training_updates'] == complete['physical_attempts'] == 0
    inputs = {r['input_id']: r for r in lines(base / 'inputs.jsonl')}
    facts = {r['input_id']: r for r in lines(base / 'private_outcomes.jsonl')}
    assert complete['model_calls'] == len(complete['rows']) == manifest['input_count'] == len(inputs)
    rows = [classify_response(item, folder=folder, request=inputs[item['input_id']]['request'],
        facts=facts[item['input_id']]) for item in complete['rows']]
    report = compare_pairs(base_report['rows'], rows, seeds={k: v['seed'] for k, v in facts.items()})
    paths = [prepared / 'manifest.json', folder / 'complete.json', base / 'report.json',
        base / 'private_outcomes.jsonl', *(folder / r['input_id'] / 'response.json' for r in rows)]
    report.update(model_calls=complete['model_calls'], physical_attempts=0, training_updates=0,
        test_used=False, identities={str(p): common.sha(p) for p in paths})
    common.save(prepared / 'report.json', report)
    print({k: report[k] for k in ('natural', 'completed', 'limitation')}, flush=True)


if __name__ == '__main__':
    main()
