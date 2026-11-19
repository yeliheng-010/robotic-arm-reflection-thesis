"""从已有规划记录重建初态，静态端点与路径检查不执行环境。"""
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from audit_motion_live import rebuild, UR5e, set_robot_config, guard_context
from goal_endpoints import enumerate_goals
from goal_search import choose
from nc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_natural_loop_v1'
SEED = 962301


def previous(case, audited):
    folder = SOURCE/'cases'/case['item']['id']
    steps = read(folder/'fixed_rule/result.json')['ledger']['steps']
    for step in steps:
        path = Path(step['session_path'])/'bridge.json'
        assert sha(path) == audited['identities'][str(path)]
        bridge = read(path)
        if bridge.get('grasp') and len(bridge['planners']) >= 2:
            return step, bridge
    return None, None


def flow_for(case, step, bridge):
    robot, env = rebuild(case, bridge['planners'][0]['context'])
    record = read(step['result_path'])['records'][0]
    pose = np.array(bridge['planners'][-1]['legs'][-1]['samples'][-1])
    assert pose.shape == (4, 4)
    np.testing.assert_allclose(pose[:3, 3], bridge['grasp']['actual_target'], atol=1e-8, rtol=0)
    return SimpleNamespace(robot=robot, env=env, q0=robot.get_joint().copy(),
        q1=np.array(record['approach_plan']['q1']), T_wo=sm.SE3(pose))


def inspect(case, audited):
    step, bridge = previous(case, audited)
    if step is None:
        return dict(id=case['item']['id'], status='no_saved_grasp_plan')
    with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}):
        flow = flow_for(case, step, bridge)
        endpoints = enumerate_goals(flow, item=case['item'])
        save(ROOT/(case['item']['id']+'_endpoints.json'), endpoints)
        plan = choose(flow, item=case['item'], parameters=step['state']['parameters'],
                      hooks=(grasp.move_to_grasp_pose, grasp.move_to_point), endpoints=endpoints)
    path = ROOT/(case['item']['id']+'_plan.json')
    save(path, plan)
    return dict(id=case['item']['id'], status=plan['status'], endpoint_passing=endpoints['passing'],
        selected=(plan['selected'] or {}).get('id'), source_step=step, plan_sha256=sha(path),
        physical_execution=False, recoverable_not_proven=True)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    audited = read(SOURCE/f'audit_{SEED}.json')
    assert audited['passed'] and audited['manifest_sha256'] == sha(SOURCE/'manifest.json')
    cases = [c for c in manifest['cases'] if c['item']['seed'] == SEED and c['item']['group']=='varied_noisy']
    assert len(cases) == 2
    save(ROOT/'manifest.json', dict(source_sha256=sha(SOURCE/'manifest.json'),
        audit_sha256=sha(SOURCE/f'audit_{SEED}.json'), cases=[c['item']['id'] for c in cases],
        identities={str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')}))
    rows = []
    for case in cases:
        row = inspect(case, audited)
        rows.append(row)
        print({k: v for k, v in row.items() if k != 'source_step'}, flush=True)
    save(ROOT/'result.json', dict(rows=rows, physical_attempts=0, model_calls=0, training_runs=0))


if __name__ == '__main__':
    main()
