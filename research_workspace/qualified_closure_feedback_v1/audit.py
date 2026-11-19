"""独立重建请求和已执行预检，不重复调用模型或动作。"""
import json
from reflection.__main__ import bootstrap
bootstrap()
from model_grasp_intent_v1.model import parse
from qualified_closure_feedback_v1.common import RUN, SEED, MAX_DECISIONS, read, save, sha, verify
from qualified_closure_feedback_v1 import inputs, policy
from qualified_closure_feedback_v1.preflight import evaluate


def audit_decision(record, *, context, history):
    ordinal = record['ordinal']
    folder, target = RUN / f'decision_{ordinal}', RUN / f'audit/decision_{ordinal}'
    expected = policy.request(context, history, remaining=MAX_DECISIONS - ordinal + 1)
    actual = read(folder / 'request.json')
    assert actual == expected
    before, after = [json.loads(x['messages'][1]['content']) for x in (context['original'], actual)]
    assert before['observation'] == after['observation'] and before['actions'] == after['actions']
    assert actual['image'] == context['original']['image']
    claim = read(folder / 'model_claim.json')
    assert claim == dict(ordinal=ordinal, consumed=1, request_sha256=sha(folder / 'request.json'))
    parsed = read(folder / 'validated.json')
    try:
        action = parse(read(folder / 'response.json'))['action']
    except (ValueError, TypeError, KeyError):
        assert not parsed['valid']
        return dict(status='invalid_model_output', stage=None), None
    assert parsed == dict(valid=True, action=action)
    result = evaluate(action, history=history, geometry=context['geometry'], folder=target)
    assert result == read(folder / 'result.json')
    for name in ('proposal.json', 'private_plan.json', 'closure.json', 'commands.json', 'preflight.json'):
        if (folder / name).exists():
            assert read(folder / name) == read(target / name), name
    return result, action


def main():
    verify()
    frozen = {str(p): sha(p) for p in RUN.rglob('*') if p.is_file()}
    summary = read(RUN / 'result.json')
    context, history, rows = inputs.context(SEED), inputs.history(), []
    for record in summary['rows']:
        assert record['ordinal'] == len(rows) + 1 <= MAX_DECISIONS
        result, action = audit_decision(record, context=context, history=history)
        assert record == dict(ordinal=len(rows) + 1, **result)
        rows.append(record)
        if result['status'] != 'rejected':
            assert len(rows) == len(summary['rows'])
            break
        history.append(policy.entry(action, result['stage']))
    assert len(rows) == summary['model_reservations'] <= MAX_DECISIONS
    assert summary['generations_started'] == summary['responses_saved'] == len(rows)
    assert summary['ready_ordinal'] == next((r['ordinal'] for r in rows if r['status'] == 'ready'), None)
    verify()
    assert all(sha(p) == digest for p, digest in frozen.items())
    save(RUN / 'audit_result.json', dict(passed=True, independent_process=True, rows=rows,
         identities=frozen, model_calls=0, physical_attempts=0, training_runs=0))
    print(dict(passed=True, rows=rows), flush=True)


if __name__ == '__main__':
    main()
