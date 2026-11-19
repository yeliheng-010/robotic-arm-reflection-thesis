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
from nc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent/'natural_capability_probe_v1'
HEIGHTS = (.10, .15, .20, .25, .30, .35, .45, .55)
SOURCES = ('revision_v2/N0_962301_varied_noisy_plan.json', 'revision_v3/N1_962301_varied_noisy_plan.json')


def examine(case, plan):
    flow = rebuild(case, plan)
    row = next(r for r in plan['prefixes'] if r['feasible'])
    parameters = plan['context']['parameters']
    segments = collect(proxy(flow, row), grasp.move_to_grasp_pose, parameters=parameters,
                       phase='prefix', route=row['approach_route'], edges=plan['edges'])
    checker = clone_robot(flow.robot)
    assert inspect(checker, flow.env, segments, item=case['item'])['feasible']
    target = plan['candidates'][0]['target']
    results = []
    for height in HEIGHTS:
        legs = collect(proxy(flow, row), grasp.move_to_point, parameters=dict(parameters, lift_height=height),
                       phase='carry', route='direct', edges=plan['edges'], target=target)
        checked = inspect(clone_robot(checker), flow.env, legs, item=case['item'])
        results.append(dict(lift_height=height, **checked))
    return dict(id=case['item']['id'], prefix_id=row['id'], target=target, results=results,
                physical_success_not_tested=True)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    save(ROOT/'manifest.json', dict(heights=list(HEIGHTS), sources={p: sha(PREVIOUS/p) for p in SOURCES},
        identities={str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.md', '.sbatch')}))
    rows = []
    for name in SOURCES:
        plan = read(PREVIOUS/name)
        case = next(c for c in manifest['cases'] if c['item']['id']+'_plan.json' == Path(name).name)
        with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}):
            row = examine(case, plan)
        save(ROOT/(case['item']['id']+'.json'), row)
        rows.append(row)
        print(row, flush=True)
    save(ROOT/'result.json', dict(rows=rows, physical_attempts=0, model_calls=0, training_runs=0))


if __name__ == '__main__':
    main()
