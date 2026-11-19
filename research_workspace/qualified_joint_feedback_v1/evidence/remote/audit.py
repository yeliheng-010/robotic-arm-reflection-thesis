"""独立进程逐条回放；不调用模型，不重新消费动作预算。"""
import json
from reflection.__main__ import bootstrap
bootstrap()
from model_grasp_intent_v1.model import parse
from model_grasp_intent_v1.geometry import propose
from qualified_path_v1.worker import inspect
from qualified_joint_feedback_v1 import inputs, policy
from qualified_joint_feedback_v1.common import ROOT, PROJECT, RUN, MAX_DECISIONS, SEEDS, read, save, sha, verify


def model_action(folder):
    recorded = read(folder/'validated.json')
    try:
        action = parse(read(folder/'response.json'))['action']
    except (ValueError, TypeError, KeyError):
        assert recorded['valid'] is False
        return None
    assert recorded == dict(valid=True, action=action)
    return action


def evaluate(folder, action, *, seed, history, geometry):
    if action is None:
        return dict(status='invalid_model_output', stage=None)
    permitted = policy.permitted(action, history)
    if permitted != 'proposal':
        assert not (folder/'private_plan.json').exists()
        return dict(status=permitted, stage=None)
    raw = read(PROJECT/f'qualified_intent_v1/run/{seed}/observation.json')
    proposal = propose(raw['target_points'], raw['nominal'], action)
    assert proposal == read(folder/'proposal.json')
    if proposal['status'] != 'proposal':
        return dict(status='rejected', stage='grasp_proposal')
    case = read(PROJECT/'qualified_task_v1/run/manifest.json')['cases'][str(seed)]
    rebuilt = inspect(case, proposal, geometry=geometry)
    assert rebuilt == read(folder/'private_plan.json')
    assert rebuilt['state_check']['passed']
    return policy.outcome(rebuilt)


def layout(seed, entries):
    context, history, rows = inputs.context(seed), inputs.history(seed), []
    for record in entries:
        ordinal = record['ordinal']
        assert ordinal == len(rows)+1 and ordinal <= MAX_DECISIONS
        folder = RUN/f'{seed}/decision_{ordinal}'
        expected = policy.request(context['original'], history, remaining=MAX_DECISIONS-ordinal+1,
            geometry=context['geometry'], grounding=context['grounding'])
        actual = read(folder/'request.json')
        assert actual == expected
        before, after = [json.loads(x['messages'][1]['content']) for x in (context['original'], actual)]
        assert before['observation'] == after['observation'] and before['actions'] == after['actions']
        assert actual['image'] == context['original']['image']
        action = model_action(folder)
        result = evaluate(folder, action, seed=seed, history=history, geometry=context['geometry'])
        assert result == read(folder/'result.json')
        assert record == dict(seed=seed, ordinal=ordinal, **result)
        rows.append(dict(record, independently_rebuilt=True))
        if result['status'] != 'rejected':
            assert len(rows) == len(entries)
            break
        history.append(policy.entry(action, result['stage']))
    return rows


def main():
    verify()
    frozen = {str(p): sha(p) for p in RUN.rglob('*') if p.is_file()}
    summary = read(RUN/'result.json')
    rows = []
    for seed in SEEDS:
        rows.extend(layout(seed, [r for r in summary['rows'] if r['seed'] == seed]))
    assert summary['model_calls'] == len(rows) <= MAX_DECISIONS*len(SEEDS)
    assert summary['ready_layouts'] == sorted({r['seed'] for r in rows if r['status'] == 'ready'})
    verify()
    assert all(sha(p) == h for p, h in frozen.items())
    save(RUN/'audit_result.json', dict(passed=True, rows=rows, identities=frozen,
        source_sha256=sha(ROOT/'audit.py'), model_calls=0, physical_attempts=0,
        training_runs=0, independent_process=True))
    print(dict(passed=True, rows=rows), flush=True)


if __name__ == '__main__':
    main()
