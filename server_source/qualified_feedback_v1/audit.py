"""独立进程复核反馈边界、原始输出和全部端点；不调用模型。"""
import json
from reflection.__main__ import bootstrap
bootstrap()
from qualified_feedback_v1 import policy
from qualified_feedback_v1.common import ROOT, PROJECT, RUN, SEED, MAX_DECISIONS, read, save, sha, verify
from qualified_intent_v1.endpoints import check
from model_grasp_intent_v1.geometry import propose
from model_grasp_intent_v1.model import parse


def evaluate(ordinal, history, *, original, case, observation):
    folder = RUN/f'decision_{ordinal}'
    request = read(folder/'request.json')
    assert request == policy.request(original, history, remaining=MAX_DECISIONS-ordinal+1)
    left, right = [json.loads(r['messages'][1]['content']) for r in (original, request)]
    right.pop('history')
    right['budget'] = left['budget']
    assert left == right and request['image'] == original['image']
    assert all(r['feedback'] == dict(status='rejected', stage='grasp_endpoint') for r in history)
    action = parse(read(folder/'response.json'))['action']
    assert action == read(folder/'validated.json')['action']
    assert policy.permitted(action, history) == 'proposal'
    proposal = propose(observation['target_points'], observation['nominal'], action)
    assert proposal == read(folder/'proposal.json')
    endpoints = check(case, proposal, seed=SEED)
    assert endpoints == read(folder/'private_endpoints.json')
    result = read(folder/'result.json')
    assert result == dict(status='ready' if endpoints['passing'] else 'rejected', passing=endpoints['passing'])
    return action, dict(ordinal=ordinal, passing=endpoints['passing'], branches=len(endpoints['rows']),
        same_observation=True, feedback_only=True, independent_rebuild_identical=True)


def main():
    verify()
    frozen = {str(p): sha(p) for p in RUN.rglob('*') if p.is_file()}
    old = PROJECT/f'qualified_intent_v1/run_v3/{SEED}'
    original = read(old/'request.json')
    history = [policy.entry(read(old/'validated.json')['action'])]
    case = read(PROJECT/'qualified_task_v1/run/manifest.json')['cases'][str(SEED)]
    observation = read(PROJECT/f'qualified_intent_v1/run/{SEED}/observation.json')
    rows = []
    for entry in read(RUN/'result.json')['rows']:
        action, row = evaluate(entry['ordinal'], history, original=original, case=case, observation=observation)
        rows.append(row)
        history.append(policy.entry(action))
    verify()
    assert all(sha(p) == h for p, h in frozen.items())
    result = dict(passed=True, rows=rows, identities=frozen, audit_sha256=sha(ROOT/'audit.py'),
        physical_attempts=0, model_calls=0, training_runs=0, independent_process=True)
    save(RUN/'audit_result.json', result)
    print(dict(passed=True, rows=rows), flush=True)


if __name__ == '__main__':
    main()
