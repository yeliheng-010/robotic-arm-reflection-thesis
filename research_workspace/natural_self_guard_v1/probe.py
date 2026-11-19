"""已审计旧现场的只读安全路径检查；不重新执行物理轨迹。"""
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import goal_search
from route_audit_v3 import rebuild
from audit_motion_live import UR5e, set_robot_config, guard_context
from rv_runtime import mode
from f_common import read, save, sha
from self_geometry import context

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_route_bridge_v2'


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    suite = unittest.defaultTestLoader.discover(str(ROOT))
    tested = unittest.TextTestRunner(verbosity=2).run(suite)
    assert tested.wasSuccessful()
    manifest, audit = read(SOURCE/'manifest.json'), read(SOURCE/'audit_962501.json')
    identities = {str(p):sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')}
    save(ROOT/'manifest.json', dict(identities=identities, tests=tested.testsRun, physical_attempts=0,
         source_manifest_sha256=sha(SOURCE/'manifest.json'), audit_sha256=sha(SOURCE/'audit_962501.json')))
    rows = []
    for case in manifest['cases']:
        if case['item']['seed'] != 962501 or case['item']['group'] != 'varied_noisy':
            continue
        path = SOURCE/'cases'/case['item']['id']/'attempt_2/route.json'
        assert sha(path) == audit['identities'][str(path)]
        trace = read(path)
        if 'context' not in trace:
            rows.append(dict(id=case['item']['id'], status='no_saved_search_context'))
            continue
        with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}), \
             context(), mode(dict(grasp_mode='world_down')), patch.object(goal_search, 'LIFTS', (.15,)):
            flow = rebuild(case, trace)
            plan = goal_search.choose(flow, item=case['item'], parameters=trace['context']['parameters'],
                                      hooks=(grasp.move_to_grasp_pose, grasp.move_to_point))
        save(ROOT/(case['item']['id']+'_plan.json'), plan)
        row = dict(id=case['item']['id'], status=plan['status'], passing=plan['endpoints']['passing'],
                   selected=(plan['selected'] or {}).get('id'))
        rows.append(row)
        print(row, flush=True)
    assert all(sha(p)==h for p,h in identities.items())
    save(ROOT/'result.json', dict(rows=rows, physical_attempts=0, model_calls=0, training_ready=False))


if __name__ == '__main__':
    main()
