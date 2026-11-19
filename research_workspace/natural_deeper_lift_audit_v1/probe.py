import os
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from audit_motion_live import UR5e, set_robot_config, guard_context
from route_audit_v3 import rebuild
from routecheck.clone import clone_robot
from waypoint_paths import collect
from waypoint_search import proxy
from route_geometry import inspect
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'natural_deeper_pilot_v1'
CASE = 'D0_962802_varied_noisy'
HEIGHTS = (.20, .25)


def examine(case, plan):
    flow = rebuild(case, plan)
    selected = plan['selected']
    assert selected and selected['feasible'] and selected['lift'] == .15
    parameters = plan['context']['parameters']
    assert parameters['grasp_offset'] == [0., 0., -.03] and parameters['time_scale'] == 3.
    segments = collect(proxy(flow, selected), grasp.move_to_grasp_pose, parameters=parameters,
        phase='prefix', route=selected['approach_route'], edges=plan['edges'])
    checker = clone_robot(flow.robot)
    assert inspect(checker, flow.env, segments, item=case['item'])['feasible']
    rows = []
    for height in HEIGHTS:
        legs = collect(proxy(flow, selected), grasp.move_to_point,
            parameters=dict(parameters, lift_height=height), phase='carry',
            route=selected['transport_route'], edges=plan['edges'], target=selected['target'])
        checked = inspect(clone_robot(checker), flow.env, legs, item=case['item'])
        rows.append(dict(lift_height=height, **checked))
    return rows


def main():
    assert os.environ.get('SLURM_JOB_ID')
    case = next(c for c in read(SOURCE/'manifest.json')['cases'] if c['item']['id'] == CASE)
    audit = read(SOURCE/'audits'/(CASE+'.json'))
    assert audit['passed'] and audit['manifest_sha256'] == sha(SOURCE/'manifest.json')
    folder = SOURCE/'cases'/CASE/'attempt_3'
    paths = [folder/'route.json', folder/'step.json', folder/'execution/result.json']
    assert all(sha(p) == audit['identities'][str(p)] for p in paths)
    record = read(paths[-1])['records'][0]
    assert record['error']['error_type'] == 'collision'
    assert record['error']['evidence']['motion_context']['phase'] == 'carry_transport'
    plan = read(folder/'route.json')
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}), \
         self_context(), joint_context(case['config']), mode(dict(grasp_mode='world_down')):
        rows = examine(case, plan)
    save(ROOT/'result.json', dict(condition=CASE, attempt=3, rows=rows, physical_attempts=0, model_calls=0,
        source_error=dict(kind='collision', phase='carry_transport'),
        limitation='Static ideal held-object route only; does not prove physical recovery or alter exhausted trajectory',
        identities={str(p):sha(p) for p in [Path(__file__), *paths, SOURCE/'audits'/(CASE+'.json')]}))
    print(rows, flush=True)


if __name__ == '__main__':
    main()
