"""数量门槛与训练许可分离；重复分支不能扩张样本量。"""


def summarize(rows):
    seed_splits, snapshot_splits = {}, {}
    for row in rows:
        assert row['split'] in ('train','dev')
        for registry, key in ((seed_splits, row['seed']), (snapshot_splits, row['snapshot_id'])):
            assert registry.setdefault(key, row['split']) == row['split'], 'Cross-split leakage'
    result = {}
    for split in ('train','dev'):
        natural = [r for r in rows if r['split']==split and r['eligible_natural']]
        recovered = [r for r in natural if r['verified_recovery']]
        result[split] = dict(snapshots=len({r['snapshot_id'] for r in natural}),
            seed_groups=len({r['seed'] for r in natural}), recoveries=len({r['snapshot_id'] for r in recovered}),
            recovery_seed_groups=len({r['seed'] for r in recovered}), tasks=sorted({r['source'] for r in natural}),
            correction_action_types=sorted({r['action']['id'] for r in recovered
                if r['action']['id'] not in ('RETRY','OBSERVE','STOP')}))
    return result


def assess(summary):
    train, dev = summary['train'], summary['dev']
    checks = dict(train_snapshots=train['snapshots']>=120, train_seeds=train['seed_groups']>=24,
        dev_snapshots=dev['snapshots']>=40, dev_seeds=dev['seed_groups']>=8,
        train_recoveries=train['recoveries']>=40, recovery_seeds=train['recovery_seed_groups']>=12,
        correction_diversity=len(train['correction_action_types'])>=2,
        train_tasks=len(train['tasks'])>=2, dev_tasks=len(dev['tasks'])>=2)
    return dict(checks=checks, quantitative_ready=all(checks.values()), training_ready=False,
        further_required=['verified_training_export', 'frozen_base_model_comparison', 'controlled_training_protocol'])
