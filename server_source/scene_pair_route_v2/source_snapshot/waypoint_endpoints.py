"""独立快速诊断：路点无法修正固定抓取/释放端点本身的不合格。"""
import os
from itertools import product
from unittest.mock import patch
import numpy as np
import mujoco
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
from manipulator_grasp.arm.robot import UR5e
from stability.kinematics import set_robot_config
from stability.prepose import inverse
from routecheck.clone import clone_robot
from route_audit_v3 import rebuild
from cm_pose import poses
from cm_geometry import sample
from cm_planning import RELEASE_OFFSET
from route_geometry import clearance, groups
from guard_scope import context as guard_context
from sd_common import read, save
from waypoint_inputs import ROOT, inputs


def check(flow, pose, *, config, item):
    robot = clone_robot(flow.robot)
    q = inverse(robot,pose,reference=flow.q1,config=config)
    if len(q) != 6:
        return dict(ok=False,reason='ik_failure')
    data = mujoco.MjData(flow.env.mj_model)
    data.qpos[:] = flow.env.mj_data.qpos
    result = sample(robot,flow.env,data,value=q,ignore=(item['source'],item['destination']))
    if result['ok']:
        result = clearance(flow.env.mj_model,data,groups(flow.env.mj_model,item['destination']))
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID')
    results = []
    for case in inputs():
        if case['reused_success']:
            continue
        with patch.object(UR5e,'set_robot_config',set_robot_config), guard_context(case['item'],{}):
            flow = rebuild(case,read(case['prior_trace']))
            rows = scan(flow,case['item'])
        output = dict(id=case['id'],rows=rows,both_endpoints_clear=sum(r['grasp']['ok'] and r['release']['ok'] for r in rows))
        results.append(output)
        print(case['id'],output['both_endpoints_clear'],flush=True)
    save(ROOT/'endpoint_diagnostic.json',results)


def scan(flow, item):
    target = flow.env.mj_data.body(item['destination']).xpos.copy()+np.array([0.,0.,RELEASE_OFFSET])
    rows = []
    for pose in poses(flow.T_wo):
        release = sm.SE3.Rt(pose['pose'].R,target)
        for config in product((1,-1),repeat=3):
            rows.append(dict(pose=pose['id'],config=list(config),
                grasp=check(flow,pose['pose'],config=config,item=item),
                release=check(flow,release,config=config,item=item)))
    return rows


if __name__ == '__main__':
    main()
