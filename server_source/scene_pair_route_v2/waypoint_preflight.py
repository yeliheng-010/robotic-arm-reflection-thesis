"""使用第二次观测的冻结上下文做CPU预检，不启动新环境尝试。"""
import os
import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from manipulator_grasp.arm.robot import UR5e
from stability.kinematics import set_robot_config
from sd_common import read, save, sha
from guard_scope import context as guard_context
from route_audit_v3 import rebuild
from waypoint_inputs import ROOT, inputs
from waypoint_search import choose


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful()
    rows = []
    for case in inputs():
        if case['reused_success']:
            continue
        with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}):
            trace = read(case['prior_trace'])
            flow = rebuild(case, trace)
            plan = choose(flow, item=case['item'], parameters=case['steps'][-1]['state']['parameters'],
                          hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))
        path = ROOT/('preflight_'+case['id']+'.json')
        assert not path.exists()
        save(path, plan)
        rows.append(dict(id=case['id'], selected=(plan['selected'] or {}).get('id'),
                         prefixes=len(plan['prefixes']), candidates=len(plan['candidates']), sha256=sha(path)))
        print(rows[-1], flush=True)
    save(ROOT/'preflight.json', dict(passed=True, tests=tests.testsRun, rows=rows))


if __name__ == '__main__':
    main()
