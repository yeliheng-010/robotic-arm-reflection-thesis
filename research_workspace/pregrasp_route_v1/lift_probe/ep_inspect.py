"""先核对预抓取终点本身，避免为不安全终点继续搜索绕行。"""
import os
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import goal_endpoints
from route_geometry import clearance, groups
from route_audit_v3 import rebuild
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent.parent
NAME = 'F0_964345_varied_noisy'


def main():
    source = PARENT/'qualification_strategy_v1/actual/cases'/NAME
    case = verify(source/'result.json')['case']
    path = PARENT/'clearance_pose_v1/probe/probe'/NAME/'plan.json'
    plan = read(path)
    rows = []
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}), \
         self_context(),joint_context(case['config']):
        for index,prefix in enumerate(plan['prefixes']):
            flow = rebuild(case,plan)
            check = goal_endpoints.sample(flow.robot,flow.env,flow.env.mj_data,
                value=np.array(prefix['q1']),ignore=(case['item']['source'],case['item']['destination']))
            if check['ok']:
                check = clearance(flow.env.mj_model,flow.env.mj_data,groups(flow.env.mj_model,case['item']['destination']))
            rows.append(dict(index=index,id=prefix['id'],q1=prefix['q1'],check=check))
    counts = Counter('passed' if r['check']['ok'] else r['check']['reason'] for r in rows)
    paths = [Path(__file__),ROOT/'endpoints.sbatch',source/'result.json',path]
    result = dict(rows=rows,counts=dict(counts),physical_attempts=0,model_calls=0,
        identities={str(p):sha(p) for p in paths})
    save(ROOT/('endpoints_'+os.environ['SLURM_JOB_ID']+'.json'),result)
    print(dict(counts=dict(counts),safe_indices=[r['index'] for r in rows if r['check']['ok']]),flush=True)


if __name__ == '__main__':
    main()
