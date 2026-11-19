def next_step(history, *, quantitative_ready, max_batches=32):
    assert history and [r['batch'] for r in history] == list(range(len(history)))
    if quantitative_ready:
        return dict(advance=False, reason='quantitative_gate_met_requires_training_review')
    if len(history)>=max_batches:
        return dict(advance=False, reason='registered_seed_budget_exhausted')
    recent = history[-3:]
    if len(recent)==3:
        if not any(r['snapshots'] for r in recent):
            return dict(advance=False, reason='three_batches_without_natural_snapshots')
        if not any(r['recoveries'] for r in recent):
            return dict(advance=False, reason='three_batches_without_verified_recovery')
        types = {t for r in history for t in r['action_types']}
        if len(types)<2:
            return dict(advance=False, reason='correction_diversity_requires_development')
        tasks = {t for r in history for t in r['tasks']}
        if len(tasks)<2:
            return dict(advance=False, reason='natural_failure_task_coverage_requires_development')
    return dict(advance=True, batch=len(history), reason='continue_registered_collection')


def shard_cases(cases, *, index, count=4):
    assert 0<=index<count
    groups = sorted({c['item']['seed'] for c in cases})
    seeds = {seed for i,seed in enumerate(groups) if i%count==index}
    return [c for c in cases if c['item']['seed'] in seeds]
