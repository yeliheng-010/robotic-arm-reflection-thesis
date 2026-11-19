import os
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
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
from f_common import read, save, sha
from span import world_points
from span_filter import context

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'natural_deeper_pilot_v1'
CASE = 'D1_962802_varied_noisy'


def main():
    assert os.environ.get('SLURM_JOB_ID')
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    evidence = read(ROOT.parent/'natural_grasp_span_audit_v1/result.json')
    recorded = next(r for r in evidence['rows'] if r['condition'] == CASE)
    assert all(sha(p) == h for p,h in recorded['identities'].items())
    case = next(c for c in read(SOURCE/'manifest.json')['cases'] if c['item']['id'] == CASE)
    folder = SOURCE/'cases'/CASE/'attempt_3'
    with np.load(folder/'execution/attempt_1/depth_evidence.npz') as data:
        depth = data['noisy']
    record = read(folder/'execution/result.json')['records'][0]
    assert not record['depth_recovery']['changed']
    mask = cv2.imread(str(folder/'execution/attempt_1/mask.png'), cv2.IMREAD_GRAYSCALE) > 0
    calibration = read(folder/'observation_summary.json')['private'][0]
    points = world_points(depth, mask, calibration)
    trace = {}
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}), \
         self_context(), joint_context(case['config']), context(points, trace), mode(dict(grasp_mode='world_down')), \
         patch.object(goal_search, 'LIFTS', (.15,)):
        flow = rebuild(case, read(folder/'route.json'))
        plan = goal_search.choose(flow, item=case['item'], parameters=read(folder/'step.json')['state']['parameters'],
            hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))
        checked = audit_plan(case, plan)
    save(ROOT/'plan.json', plan)
    save(ROOT/'result.json', dict(condition=CASE, tests=tested.testsRun, poses=trace['poses'],
        status=plan['status'], selected=(plan['selected'] or {}).get('id'), independent_static_audit=checked,
        physical_attempts=0, model_calls=0, physical_recovery_not_tested=True,
        identities={str(p):sha(p) for p in [*ROOT.glob('*.py'), ROOT/'plan.json']}))
    print(dict(tests=tested.testsRun, status=plan['status'], selected=(plan['selected'] or {}).get('id')), flush=True)


if __name__ == '__main__':
    main()
