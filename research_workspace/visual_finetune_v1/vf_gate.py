"""数量、数据身份与真实可学习缺陷同时具备才允许试训。"""
DEFECTS = {'invalid_output', 'stop_before_completion', 'observed_failure'}
MIN_DEFECT_SEEDS = 3


def check_ready(dataset, audit, comparison, private):
    assert dataset['gate']['quantitative_ready'], 'Original quantitative gate not met'
    assert audit['passed'] and audit['quantitative_ready']
    assert comparison['physical_attempts'] == comparison['training_updates'] == 0
    assert comparison['inputs'] == len(comparison['rows']) == len(private)
    assert comparison['model_calls'] == len(private)
    facts = {r['input_id']: r for r in private}
    assert len(facts) == len(private)
    seeds, snapshots = set(), set()
    for row in comparison['rows']:
        evidence = facts[row['input_id']]
        assert row['snapshot_id'] == evidence['snapshot_id']
        recoverable = any(o['success'] is True for o in evidence['outcomes'])
        if not evidence['completed'] and recoverable and row['model'] in DEFECTS:
            seeds.add(evidence['seed'])
            snapshots.add(evidence['snapshot_id'])
    assert len(seeds) >= MIN_DEFECT_SEEDS, 'Insufficient verified learnable base-model defects'
    return dict(defect_seed_groups=len(seeds), defect_snapshots=len(snapshots),
        criterion='known_success_option_available_and_base_invalid_stop_or_observed_failure')
