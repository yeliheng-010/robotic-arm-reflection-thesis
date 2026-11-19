import subprocess
from reflection.__main__ import bootstrap
bootstrap()
from qualified_intent_v1.model_v3 import verified as prior, OUTPUT as PREVIOUS
from qualified_intent_v1.endpoints import check
from model_grasp_intent_v1.geometry import propose
from qualified_feedback_v1 import policy
from qualified_feedback_v1.common import ROOT, PROJECT, RUN, SEED, MAX_DECISIONS, read, save, sha, verify


def prepare():
    old = prior()
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md')]
    paths.extend(PREVIOUS/str(SEED)/n for n in ('request.json', 'validated.json', 'private_endpoints.json'))
    identities = dict(old['identities'])
    identities.update({str(p): sha(p) for p in paths})
    assert read(PREVIOUS/f'{SEED}/private_endpoints.json')['passing'] == 0
    save(RUN/'manifest.json', dict(seed=SEED, identities=identities, max_model_calls=MAX_DECISIONS,
        max_endpoint_checks=MAX_DECISIONS*8, max_task_attempts=0, max_training_runs=0,
        feedback='Only action and rejected/grasp_endpoint; no collision names or correction answers'))


def inspect(action, folder, *, history, case, observation):
    status = policy.permitted(action, history)
    if status != 'proposal':
        return dict(status=status, passing=0)
    proposal = propose(observation['target_points'], observation['nominal'], action)
    save(folder/'proposal.json', proposal)
    if proposal['status'] != 'proposal':
        return dict(status='proposal_rejected', passing=0)
    result = check(case, proposal, seed=SEED)
    save(folder/'private_endpoints.json', result)
    return dict(status='ready' if result['passing'] else 'rejected', passing=result['passing'])


def main():
    prepare()
    original = read(PREVIOUS/f'{SEED}/request.json')
    history = [policy.entry(read(PREVIOUS/f'{SEED}/validated.json')['action'])]
    case = read(PROJECT/'qualified_task_v1/run/manifest.json')['cases'][str(SEED)]
    observation = read(PROJECT/f'qualified_intent_v1/run/{SEED}/observation.json')
    rows = []
    for ordinal in range(1, MAX_DECISIONS+1):
        folder = RUN/f'decision_{ordinal}'
        save(folder/'request.json', policy.request(original, history, remaining=MAX_DECISIONS-ordinal+1))
        subprocess.run(['bash', str(ROOT/'model.sh'), str(ordinal)], check=True, timeout=360)
        parsed = read(folder/'validated.json')
        if not parsed['valid']:
            result = dict(status='invalid_model_output', passing=0)
        else:
            result = inspect(parsed['action'], folder, history=history, case=case, observation=observation)
        save(folder/'result.json', result)
        rows.append(dict(ordinal=ordinal, **result))
        if result['status'] in ('ready', 'model_stopped', 'invalid_model_output', 'unsupported_action'):
            break
        history.append(policy.entry(parsed['action']))
    verify()
    save(RUN/'result.json', dict(rows=rows, model_calls=len(rows), physical_attempts=0,
        training_runs=0, full_path_verified=False, improved=any(r['passing'] for r in rows)))
    print(rows, flush=True)


if __name__ == '__main__':
    main()
