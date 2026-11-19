"""真实初态的只读关节搜索，每条检查立即追加到账本。"""
import json
import time
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from route_audit_v3 import rebuild
from audit_motion_live import UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from js_rrt import search
from js_geometry import EdgeChecker, option
from js_common import RUN, OPTIONS, MAX_GOALS, inputs, freeze, save, sha, verify


def goals(plan):
    seen, rows = set(), []
    for index,row in enumerate(plan['prefixes']):
        key = tuple(row['q1'])
        if key not in seen:
            rows.append(dict(index=index,id=row['id'],q1=row['q1']))
            seen.add(key)
    return rows[:MAX_GOALS]


def logger(stream, checker):
    def record(event):
        event['check'] = checker.last
        stream.write(json.dumps(event,allow_nan=False)+'\n')
        stream.flush()
        if event['index'] % 100 == 0:
            print(dict(checks=event['index']),flush=True)
    return record


def run(case, plan, bounds):
    rows, selected = [], None
    for index,goal in enumerate(goals(plan)):
        flow = rebuild(case,plan)
        checker = EdgeChecker(flow,case)
        path = RUN/f'edges_{index}.jsonl'
        started = time.monotonic()
        with path.open('x') as stream:
            result = search(plan['context']['q0'],goal['q1'],bounds=bounds.tolist(),
                check=checker,seed=42+index,on_check=logger(stream,checker),**OPTIONS)
        row = dict(goal=goal,result=result,elapsed=time.monotonic()-started,ledger_sha256=sha(path))
        save(RUN/f'goal_{index}.json',row)
        rows.append(row)
        print(dict(goal=index,status=result['status'],checks=result['checks'],nodes=result['nodes']),flush=True)
        if result['path'] is not None:
            selected = dict(goal=goal,path=result['path'],
                            option=option(result['path'],checker.minimum),source_goal=index)
            break
    return rows, selected


def main():
    assert not RUN.exists(), 'Consumed search cannot be rerun'
    freeze()
    case, plan = inputs()
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}), \
         self_context(),joint_context(case['config']) as bounds:
        rows, selected = run(case,plan,bounds)
    verify(RUN/'manifest.json')
    paths = [*RUN.glob('goal_*.json'),*RUN.glob('edges_*.jsonl')]
    save(RUN/'result.json',dict(selected=selected,rows=rows,physical_attempts=0,model_calls=0,
        scope='pregrasp only; not complete-task qualification',
        identities={str(p):sha(p) for p in paths}))


if __name__ == '__main__':
    main()
