"""有限枚举等价关节终点，保存每条原保护器的检查结果。"""
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from route_audit_v3 import rebuild
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from js_geometry import EdgeChecker, option
from js_probe import goals
from js_common import inputs, RUN as SEARCH, SOURCE, PRIOR, read, save, sha, verify
from jr_angles import candidates

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'probe'
MAX_VARIANTS = 32


def run(case, plan, bounds):
    flow = rebuild(case,plan)
    checker = EdgeChecker(flow,case)
    start = plan['context']['q0']
    count = 0
    for index,row in enumerate(goals(plan)):
        options = candidates(start,row['q1'],bounds=bounds.tolist())
        assert len(options) <= MAX_VARIANTS
        for variant,goal in enumerate(options):
            np.testing.assert_allclose(flow.robot.fkine(np.array(goal)).A,
                flow.robot.fkine(np.array(row['q1'])).A,atol=1e-8,rtol=0)
            feasible = checker(start,goal)
            record = dict(goal=row,variant=variant,path=[start,goal],check=checker.last,
                option=option([start,goal],checker.minimum))
            save(RUN/f'candidate_{index}_{variant}.json',record)
            count += 1
            if feasible:
                return record,count
    return None,count


def main():
    assert not RUN.exists()
    previous = verify(SEARCH/'manifest.json')
    paths = [SOURCE/'result.json',PRIOR,*ROOT.glob('*.py'),*ROOT.glob('*.sh'),*ROOT.glob('*.sbatch')]
    identities = dict(previous['identities'])
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(identities=identities,max_goals=8,max_variants=MAX_VARIANTS,
        physical_attempts=0,model_calls=0,description='Equivalent angles; identical end-effector FK'))
    case,plan = inputs()
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}), \
         self_context(),joint_context(case['config']) as bounds:
        selected,count = run(case,plan,bounds)
    verify(RUN/'manifest.json')
    save(RUN/'result.json',dict(selected=selected,checked=count,physical_attempts=0,model_calls=0,
        scope='pregrasp only',identities={str(p):sha(p) for p in RUN.glob('candidate_*.json')}))
    print(dict(selected=selected,checked=count),flush=True)


if __name__ == '__main__':
    main()
