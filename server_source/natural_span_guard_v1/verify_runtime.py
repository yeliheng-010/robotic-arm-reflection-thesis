import os
import shutil
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
from span_runtime import capture_data, choose_wrapper
from span_audit import reconstruct
from span_filter import context as filter_context

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'natural_deeper_pilot_v1/cases/D1_962802_varied_noisy/attempt_3'


def verify_sources(folder):
    files = ('execution/result.json', 'execution/attempt_1/depth_evidence.npz', 'execution/attempt_1/mask.png')
    for name in files:
        target = folder/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE/name, target)
        assert sha(target) == sha(SOURCE/name)
    world, trace = reconstruct(folder)
    assert world is not None and trace['active']


def main():
    assert os.environ.get('SLURM_JOB_ID')
    previous = read(ROOT/'result.json')
    assert all(sha(p) == h for p,h in previous['identities'].items())
    folder = ROOT/'runtime_check'
    folder.mkdir(exist_ok=False)
    with np.load(SOURCE/'execution/attempt_1/depth_evidence.npz') as arrays:
        depth = arrays['noisy']
    mask = cv2.imread(str(SOURCE/'execution/attempt_1/mask.png'), cv2.IMREAD_GRAYSCALE)
    rgb = cv2.imread(str(SOURCE/'execution/attempt_1/before.png'))
    case = next(c for c in read(SOURCE.parents[2]/'manifest.json')['cases'] if c['item']['id'] == SOURCE.parent.name)
    calibration = read(SOURCE/'observation_summary.json')['private'][0]
    fovy = 2*np.arctan(depth.shape[0]/(2*calibration['intrinsics'][1]))
    captured, trace = {}, dict(active=False)
    capture_data(grasp.get_and_process_data, captured)(rgb, depth, mask, fovy=fovy)
    choose = choose_wrapper(goal_search.choose, captured, folder=folder, trace=trace)
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}), \
         self_context(), joint_context(case['config']), mode(dict(grasp_mode='world_down')), \
         patch.object(goal_search, 'LIFTS', (.15,)):
        flow = rebuild(case, read(SOURCE/'route.json'))
        plan = choose(flow, item=case['item'], parameters=read(SOURCE/'step.json')['state']['parameters'],
            hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))
        with filter_context(captured['points']@np.array(trace['transform'])[:3,:3].T+np.array(trace['transform'])[:3,3], {}):
            checked = audit_plan(case, plan)
    save(folder/'span_guard.json', trace)
    save(folder/'route.json', plan)
    verify_sources(folder)
    # 这些只是旧数据构建的审计fixture，0新物理。
    with np.load(trace['artifact']) as arrays:
        rebuilt = grasp.get_and_process_data(rgb, arrays['depth'], arrays['mask'], fovy=trace['fovy'])
        np.testing.assert_array_equal(np.asarray(rebuilt[1].points), arrays['camera_points'])
    np.testing.assert_allclose(calibration['transform'], trace['transform'], rtol=0, atol=1e-12)
    save(folder/'verification.json', dict(passed=True, static_audit=checked, model_calls=0, physical_attempts=0,
        identities={str(p):sha(p) for p in [*ROOT.glob('*.py'), folder/'span_guard.json', folder/'route.json']}))


if __name__ == '__main__':
    main()
