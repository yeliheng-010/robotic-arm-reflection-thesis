from collections import Counter
from pathlib import Path
from f_common import read, sha
from policy import eligible, snapshot
from check_input import public


def decisions(branch, case):
    views = [read(ref['path']) for ref in branch['views']]
    rows = []
    for event in branch['decisions']:
        index = event['after_attempt']-1
        step = branch['ledger']['steps'][index]
        assert not step['success']
        initial = next(v for v in views if v['public'][0]['attempt'] == step['index'])
        action = event.get('action')
        executes = event['status'] == 'proposed' and action is not None and action['id'] not in ('STOP','OBSERVE')
        following = branch['ledger']['steps'][index+1] if executes else None
        assert sha(event['input_path']) == event['input_sha256']
        bundle = read(event['input_path'])
        public(bundle['request'])
        record = read(step['result_path'])['records'][0]
        allowed, reason = eligible(record)
        rows.append(dict(snapshot_id=snapshot(case['item'], initial), condition=case['item']['id'],
            seed=case['item']['seed'], group=case['item']['group'], split=case['item']['split'],
            source=case['item']['source'], destination=case['item']['destination'], method=branch['method'],
            input_path=event['input_path'], input_sha256=event['input_sha256'], status=event['status'], action=action,
            before=step, successor=following, eligible_natural=allowed, private_eligibility_reason=reason,
            verified_recovery=bool(allowed and following and following['success']),
            supervision_claim='verified_corrective_reset_execution_not_optimal_action_or_causal_label'))
    return rows


def collect(source):
    manifest, complete = read(source/'manifest.json'), read(source/'complete.json')
    assert complete['passed'] and all(sha(p) == h for p,h in manifest['identities'].items())
    rows, conditions, identities = [], [], {}
    for case in manifest['cases']:
        name = case['item']['id']
        path = source/'audits'/(name+'.json')
        audit = read(path)
        assert audit['passed'] and audit['manifest_sha256'] == sha(source/'manifest.json')
        assert all(sha(p) == h for p,h in audit['identities'].items())
        identities[str(path)] = sha(path)
        folder = source/'cases'/name
        first = read(folder/'first/step.json')
        record = read(first['result_path'])['records'][0]
        allowed, reason = (False, 'first_success') if first['success'] else eligible(record)
        result = read(folder/'result.json')
        conditions.append(dict(id=name, seed=case['item']['seed'], group=case['item']['group'],
            first_success=first['success'], first_eligible_natural=allowed, private_first_reason=reason,
            methods=result['methods']))
        for method in ('fixed_rule','direct','diagnostic'):
            rows.extend(decisions(read(folder/method/'result.json'), case))
    return rows, conditions, identities


def summarize(rows):
    natural = [r for r in rows if r['eligible_natural']]
    recovered = [r for r in natural if r['verified_recovery']]
    return dict(decisions=len(rows), unique_natural_snapshots=len({r['snapshot_id'] for r in natural}),
        verified_natural_recoveries=len({r['snapshot_id'] for r in recovered}),
        correction_action_types=sorted({r['action']['id'] for r in recovered if r['action']['id'] != 'RETRY'}),
        natural_seed_groups=sorted({r['seed'] for r in natural}), recovery_seed_groups=sorted({r['seed'] for r in recovered}),
        natural_tasks=sorted({r['source'] for r in natural}),
        exclusions=dict(Counter(r['private_eligibility_reason'] for r in rows if not r['eligible_natural'])),
        decision_statuses=dict(Counter(r['status'] for r in rows)),
        action_counts=dict(Counter(r['action']['id'] for r in rows if r['action'] is not None)),
        pilot_is_training_data=False, training_ready=False)


def metrics(conditions):
    output = {}
    for group in ('baseline','varied_noisy'):
        subset = [r for r in conditions if r['group'] == group]
        output[group] = dict(conditions=len(subset), first_success=sum(r['first_success'] for r in subset),
            first_natural_failures=sum(r['first_eligible_natural'] for r in subset), methods={})
        for method in ('fixed_rule','direct','diagnostic'):
            output[group]['methods'][method] = dict(success=sum(r['methods'][method]['success'] for r in subset),
                recovery_from_first_natural=sum(r['first_eligible_natural'] and r['methods'][method]['success'] for r in subset),
                model_calls=sum(r['methods'][method]['model_calls'] for r in subset))
    return output
