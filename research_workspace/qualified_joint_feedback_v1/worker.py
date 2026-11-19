import subprocess
from reflection.__main__ import bootstrap
bootstrap()
from model_grasp_intent_v1.geometry import propose
from qualified_path_v1.worker import inspect
from qualified_joint_feedback_v1 import inputs, policy
from qualified_joint_feedback_v1.common import ROOT, PROJECT, RUN, SEEDS, MAX_DECISIONS, read, save, verify


def evaluate(action, folder, *, seed, history, geometry):
    permitted = policy.permitted(action, history)
    if permitted != 'proposal':
        return dict(status=permitted, stage=None)
    observation = read(PROJECT/f'qualified_intent_v1/run/{seed}/observation.json')
    proposal = propose(observation['target_points'], observation['nominal'], action)
    save(folder/'proposal.json', proposal)
    if proposal['status'] != 'proposal':
        return dict(status='rejected', stage='grasp_proposal')
    case = read(PROJECT/'qualified_task_v1/run/manifest.json')['cases'][str(seed)]
    result = inspect(case, proposal, geometry=geometry)
    save(folder/'private_plan.json', result)
    return policy.outcome(result)


def run(seed):
    context, history, rows = inputs.context(seed), inputs.history(seed), []
    for ordinal in range(1, MAX_DECISIONS+1):
        folder = RUN/f'{seed}/decision_{ordinal}'
        request = policy.request(context['original'], history, remaining=MAX_DECISIONS-ordinal+1,
            geometry=context['geometry'], grounding=context['grounding'])
        save(folder/'request.json', request)
        subprocess.run(['bash', str(ROOT/'model.sh'), str(seed), str(ordinal)], check=True, timeout=360)
        parsed = read(folder/'validated.json')
        if not parsed['valid']:
            result = dict(status='invalid_model_output', stage=None)
        else:
            result = evaluate(parsed['action'], folder, seed=seed, history=history, geometry=context['geometry'])
        save(folder/'result.json', result)
        rows.append(dict(seed=seed, ordinal=ordinal, **result))
        print(rows[-1], flush=True)
        if result['status'] != 'rejected':
            break
        history.append(policy.entry(parsed['action'], result['stage']))
    return rows


def main():
    verify()
    rows = []
    for seed in SEEDS:
        rows.extend(run(seed))
    verify()
    save(RUN/'result.json', dict(rows=rows, model_calls=len(rows), physical_attempts=0,
        training_runs=0, ready_layouts=sorted({r['seed'] for r in rows if r['status'] == 'ready'})))


if __name__ == '__main__':
    main()
