"""重建固定含噪快照，复用已审计的抓取族，不挑种子。"""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import goal_endpoints
import top_runtime
from route_audit_v3 import rebuild
from audit_motion_live import UR5e,set_robot_config,guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rv_runtime import mode
from lc_candidates import candidates
from cc_common import read


@contextmanager
def opened(entry):
    case=entry['case']
    old=read(entry['plan'])
    with np.load(Path(entry['folder'])/'span_inputs.npz') as arrays:
        points=arrays['world_points']
    trace={}
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}), \
         self_context(),joint_context(case['config']),mode(case['control']), \
         patch.object(top_runtime,'candidates',candidates),top_runtime.filter_context(points,trace):
        flow=rebuild(case,old)
        poses={r['id']:r['pose'] for r in goal_endpoints.poses(flow.T_wo)}
        previous=read(entry['long_plan'])
        assert trace==read(Path(entry['long_plan']).with_name('trace.json'))['candidate_stages'][-1]
        grasps=[r for r in previous['endpoints']['grasps'] if r['ok']]
        for row in grasps:
            checked=goal_endpoints.inspect(flow,poses[row['pose']],config=row['config'],item=case['item'])
            assert checked=={k:v for k,v in row.items() if k not in ('id','pose','config')}
        yield flow,grasps,poses
