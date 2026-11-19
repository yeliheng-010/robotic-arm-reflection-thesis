"""重建已有五个回程状态，只检查规划，不执行机械臂运动。"""
import os
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from audit_motion_live import rebuild, group, UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from rh_planner import select
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'task_accuracy_v1/pilot'


def probe(case):
    seed = case['item']['seed']
    path = SOURCE/'cases'/str(seed)/'first/bridge.json'
    bridge = read(path)
    row = bridge['planners'][-1]
    assert row['action'] == 'back_to_zero' and len(row['legs']) == 1
    with patch.object(UR5e, 'set_robot_config', set_robot_config), \
         guard_context(case['item'], {}), self_context(), joint_context(case['config']):
        original = group(case, row)
        robot, env = rebuild(case, row['context'])
        goal = row['legs'][0]['samples'][-1]
        result = select(robot, env, goal, duration=row['legs'][0]['duration'], item=case['item'])
    if original['feasible']:
        assert result['selected']['id'] == 'direct'
    return dict(seed=seed, original=original, result=result, source=str(path), source_sha256=sha(path))


def main():
    manifest = verify(SOURCE/'manifest.json')
    cases = manifest['cases']
    rows = [probe(case) for case in cases]
    files = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')]
    identities = {str(p): sha(p) for p in files}
    identities[str(SOURCE/'manifest.json')] = sha(SOURCE/'manifest.json')
    save(ROOT/'probes'/('job_'+os.environ['SLURM_JOB_ID'])/'result.json', dict(rows=rows,
        identities=identities, physical_attempts=0, model_calls=0,
        all_admissible=all(r['result']['selected'] is not None for r in rows)))
    print([dict(seed=r['seed'], original=r['original']['feasible'],
        selected=(r['result']['selected'] or {}).get('id'), candidates=len(r['result']['attempts']))
        for r in rows], flush=True)


if __name__ == '__main__':
    main()
