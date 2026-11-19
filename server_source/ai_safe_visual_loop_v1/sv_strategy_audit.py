from pathlib import Path
from live_telemetry import Recorder
from cp_audit import candidate_audit
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode
from sr_audit import measured
from top_audit import audit_attempt
from sv_strategy_actions import apply
from sv_common import read


def inspect(case, step):
    assert step['control'] == case['control'] == dict(grasp_mode='world_down')
    with self_context(), joint_context(case['config']), mode(step['control']):
        record, geometry = audit_attempt(case, step)
    candidate_audit(step, case['config'])
    folder = Path(step['session_path'])
    contact = measured(folder)
    assert contact['self_contact_samples'] == 0
    recorder = Recorder()
    recorder.rows = read(folder/'telemetry.json')['rows']
    return dict(record=record, recorder=recorder, geometry=geometry,
        contact={k:v for k,v in contact.items() if k != 'closing_end'})


def advance(branch, action, *, steps, summaries, cursor):
    current, following = summaries[cursor:cursor+2]
    if action['id'] == 'OBSERVE':
        branch.observe()
        assert following['paths'][:-1] == current['paths']
        assert following['public'][:-1] == current['public']
        assert following['public'][-1]['attempt'] == len(branch.ledger['steps'])
    else:
        state, strategy = apply(branch.ledger['steps'][-1], action)
        step = steps[len(branch.ledger['steps'])]
        assert step['state'] == state and step['strategy'] == strategy
        branch.append(step)
        assert len(following['paths']) == 1 and following['public'][0]['attempt'] == step['index']
    assert following['remaining'] == branch.remaining
    return cursor+1
