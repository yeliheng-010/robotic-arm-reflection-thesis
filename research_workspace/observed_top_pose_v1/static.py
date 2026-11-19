import os
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import goal_search
from audit_motion_live import UR5e, set_robot_config, guard_context
from route_audit_v3 import rebuild
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode
from goal_audit_geometry_v2 import audit as audit_plan
from top_runtime import filter_context
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'natural_span_pilot_v1'
CASES = ('P0_963001_baseline', 'P0_963008_varied_noisy')


def examine(name):
    folder = SOURCE/'cases'/name/'attempt_1'
    case = next(c for c in read(SOURCE/'manifest.json')['cases'] if c['item']['id'] == name)
    audited = read(SOURCE/'audits'/(name+'.json'))
    assert audited['passed'] and all(sha(p) == h for p,h in audited['identities'].items())
    previous = read(folder/'route.json')
    with np.load(folder/'span_inputs.npz') as arrays:
        points = arrays['world_points']
    trace = {}
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}), \
         self_context(), joint_context(case['config']), mode(dict(grasp_mode='world_down')), \
         filter_context(points, trace), patch.object(goal_search, 'LIFTS', (.20,)):
        flow = rebuild(case, previous)
        plan = goal_search.choose(flow, item=case['item'], parameters=case['state']['parameters'],
            hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))
        checked = audit_plan(case, plan)
    save(ROOT/'static'/name/'plan.json', plan)
    return dict(id=name, selected=plan['selected'] is not None, status=plan['status'],
        endpoint_passing=plan['endpoints']['passing'], fit=trace, audit=checked)


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'static').exists()
    prior = read(ROOT/'result.json')
    assert all(sha(p) == h for p,h in prior['identities'].items())
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    rows = [examine(name) for name in CASES]
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py','.md','.sbatch')]
    save(ROOT/'static/result.json', dict(rows=rows, tests=tested.testsRun, physical_attempts=0,
        model_calls=0, training_ready=False, identities={str(p):sha(p) for p in paths}))
    print([dict(id=r['id'], selected=r['selected'], status=r['status']) for r in rows], flush=True)


if __name__ == '__main__':
    main()
