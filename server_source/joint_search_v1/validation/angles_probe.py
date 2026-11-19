"""只读核对预抓取的等价角表示是否引入额外整圈运动。"""
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from route_audit_v3 import rebuild
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from bounded_ik import representatives
from js_geometry import EdgeChecker
from js_probe import goals
from js_common import ROOT, RUN, inputs, save, sha, verify


def main():
    verify(RUN/'manifest.json')
    case,plan = inputs()
    rows = []
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}), \
         self_context(),joint_context(case['config']) as bounds:
        flow = rebuild(case,plan)
        start = plan['context']['q0']
        for row in goals(plan):
            goal = representatives(row['q1'],start,bounds)
            np.testing.assert_allclose(flow.robot.fkine(goal).A,
                                       flow.robot.fkine(np.array(row['q1'])).A,atol=1e-8,rtol=0)
            changed = not np.allclose(goal,row['q1'],atol=1e-12,rtol=0)
            value = dict(goal=row,nearest=goal.tolist(),changed=changed)
            if changed:
                checker = EdgeChecker(flow,case)
                checker(start,goal.tolist())
                value['direct'] = checker.last
            rows.append(value)
    paths = [ROOT/'validation/angles_probe.py',ROOT/'validation/angles.sbatch',RUN/'manifest.json']
    save(ROOT/'validation/angles.json',dict(bounds=bounds.tolist(),rows=rows,
        physical_attempts=0,model_calls=0,identities={str(p):sha(p) for p in paths}))
    print(dict(changed=sum(r['changed'] for r in rows),
        direct_passed=sum(r.get('direct',{}).get('feasible',False) for r in rows)),flush=True)


if __name__ == '__main__':
    main()
