"""保存完整端点账本后再限额搜索路径；不渲染、不推进真实物理。"""
import os
import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from manipulator_grasp.arm.robot import UR5e
from stability.kinematics import set_robot_config
from guard_scope import context as guard_context
from route_audit_v3 import rebuild
from sd_common import read,save,sha
from goal_inputs import ROOT,inputs
from goal_endpoints import enumerate_goals
from goal_search import choose


def run(case):
    with patch.object(UR5e,'set_robot_config',set_robot_config), guard_context(case['item'],{}):
        flow=rebuild(case,read(case['prior_trace']))
        endpoints=enumerate_goals(flow,item=case['item'])
        path=ROOT/('endpoints_'+case['id']+'.json')
        assert not path.exists()
        save(path,endpoints)
        print(case['id'],'endpoint passing',endpoints['passing'],flush=True)
        plan=choose(flow,item=case['item'],parameters=case['steps'][-1]['state']['parameters'],
                    hooks=(grasp.move_to_grasp_pose,grasp.move_to_point),endpoints=endpoints)
    target=ROOT/('preflight_'+case['id']+'.json')
    save(target,plan)
    result=dict(id=case['id'],status=plan['status'],selected=(plan['selected'] or {}).get('id'),
                prefixes=len(plan['prefixes']),carry=len(plan['candidates']),
                sha256=sha(target),endpoints_sha256=sha(path))
    print(result,flush=True)
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID')
    tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful()
    rows=[run(c) for c in inputs() if not c['reused_success']]
    save(ROOT/'preflight.json',dict(passed=True,rows=rows,tests=tests.testsRun))


if __name__=='__main__':
    main()
