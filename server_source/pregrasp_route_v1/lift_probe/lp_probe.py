"""固定抬臂关节路点的只读验证；每个已检候选立即留账。"""
import os
import math
from itertools import product
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from route_audit_v3 import rebuild
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rh_planner import evaluate
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent.parent
NAME = 'F0_964345_varied_noisy'
MAX_PREFIXES = 8
SPEED_LIMIT = 1.0
ACCELERATION_LIMIT = 2.0
QUINTIC_PEAK_SPEED = 1.875
QUINTIC_PEAK_ACCELERATION = 10/math.sqrt(3)


def duration(start, end, minimum):
    distance = max(abs(a-b) for a,b in zip(start,end))
    return max(minimum, QUINTIC_PEAK_SPEED*distance/SPEED_LIMIT,
               math.sqrt(QUINTIC_PEAK_ACCELERATION*distance/ACCELERATION_LIMIT))


def options(start, goal, minimum):
    for shoulder, elbow, wrist_goal in product((-math.pi/2,math.pi/2), (0.,math.pi/2,-math.pi/2), (True,False)):
        first = list(start)
        first[1:3] = [shoulder,elbow]
        if wrist_goal:
            first[3:] = goal[3:]
        second = list(first)
        second[0] = goal[0]
        points = [list(start)]
        for point in (first,second,list(goal)):
            if point != points[-1]:
                points.append(point)
        times = [duration(a,b,minimum) for a,b in zip(points,points[1:])]
        yield dict(id=f'raised_{shoulder}_{elbow}_{wrist_goal}', waypoints=points, durations=times)


def search(case, plan, prefixes, output):
    results = []
    with patch.object(UR5e,'set_robot_config',set_robot_config), guard_context(case['item'],{}), \
         self_context(), joint_context(case['config']):
        for index, prefix in enumerate(prefixes[:MAX_PREFIXES]):
            for option_index, option in enumerate(options(plan['context']['q0'],prefix['q1'],
                                                         case['state']['parameters']['time_scale'])):
                flow = rebuild(case,plan)
                result = evaluate(option,flow.robot,flow.env,item=case['item'])
                row = dict(prefix_index=index, prefix_id=prefix['id'], option=option, check=result)
                save(output/f'candidate_{index}_{option_index}.json',row)
                results.append(row)
                if result['feasible']:
                    repeated = evaluate(option,flow.robot,flow.env,item=case['item'])
                    assert result == repeated
                    return results,row
    return results,None


def main():
    source = PARENT/'qualification_strategy_v1/actual/cases'/NAME
    recorded = verify(source/'result.json')
    plan = read(source/'actual_plan.json')
    path = PARENT/'clearance_pose_v1/probe/probe'/NAME/'plan.json'
    previous = read(path)
    assert all(r['phase']=='pregrasp' and not r['feasible'] for r in previous['prefixes'])
    output = ROOT/'run'
    assert not output.exists()
    paths = [Path(__file__), ROOT/'run.sbatch', path, source/'result.json',source/'actual_plan.json']
    save(output/'manifest.json',dict(max_prefixes=MAX_PREFIXES,max_routes_per_prefix=12,
        speed_limit=SPEED_LIMIT,acceleration_limit=ACCELERATION_LIMIT,
        identities={str(p):sha(p) for p in paths},physical_attempts=0))
    results,selected = search(recorded['case'],plan,previous['prefixes'],output)
    save(output/'result.json',dict(selected=selected,checked=len(results),
        identities={str(p):sha(p) for p in output.glob('candidate_*.json')},
        physical_attempts=0,model_calls=0,limitation='Joint pregrasp only; not complete task feasibility'))
    print(dict(checked=len(results),selected=selected),flush=True)


if __name__ == '__main__':
    main()
