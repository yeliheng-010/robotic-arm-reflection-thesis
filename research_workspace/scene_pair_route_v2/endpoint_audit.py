"""独立端点剪枝证据；不把取消的全路径搜索当作已完成。"""
import os
import unittest
from itertools import product
from collections import Counter
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from manipulator_grasp.arm.robot import UR5e
from stability.kinematics import set_robot_config
from cm_pose import poses
from guard_scope import context as guard_context
from route_audit_v3 import rebuild
from sd_common import read, save, sha
from waypoint_inputs import ROOT, PREVIOUS, inputs
from endpoint_geometry import inspect


def freeze(cases):
    assert not (ROOT/'manifest.json').exists()
    identities = dict(read(PREVIOUS/'manifest.json')['identities'])
    paths = [*ROOT.rglob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md',
             ROOT/'endpoint_diagnostic.json', PREVIOUS/'manifest.json',PREVIOUS/'verification.json']
    for case in cases:
        paths += [s['result_path'] for s in case['steps']]
        if 'prior_trace' in case:
            paths.append(case['prior_trace'])
    identities.update({str(p):sha(p) for p in paths})
    for path,digest in identities.items():
        assert sha(path)==digest,path
    manifest = dict(cases=cases,selected=[],identities=identities,stage='endpoint_pruning_before_execution',
                    cancelled_jobs=[5807,5812],full_path_search_completed=False,max_attempts=3,
                    actual_new_attempts=0,promotion_allowed=False,training_approved=False)
    save(ROOT/'manifest.json',manifest)
    return manifest


def validate(case, diagnostic):
    trace = read(case['prior_trace'])
    audit_path = PREVIOUS/'physics'/case['id']/'attempt_2/audit.json'
    assert read(audit_path)['route_sha256']==sha(case['prior_trace'])
    with patch.object(UR5e,'set_robot_config',set_robot_config), guard_context(case['item'],{}):
        flow = rebuild(case,trace)
        expected = [(p['id'],list(c)) for p in poses(flow.T_wo) for c in product((1,-1),repeat=3)]
        assert [(r['pose'],r['config']) for r in diagnostic['rows']]==expected
        assert len(expected)==72
        measurements = inspect(flow,diagnostic['rows'],item=case['item'],
                               parameters=case['steps'][-1]['state']['parameters'])
    save(ROOT/('endpoint_audit_'+case['id']+'.json'),measurements)
    counts = dict(Counter(r['reason'] for r in measurements))
    return dict(id=case['id'],release_endpoints=72,release_clear=0,release_reasons=counts,
                grasp_clear=sum(r['grasp']['ok'] for r in diagnostic['rows']),
                success=False,actual_new_attempts=0,third_attempt_used=False,
                independent_geometry_sha256=sha(ROOT/('endpoint_audit_'+case['id']+'.json')))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tests.wasSuccessful()
    cases = inputs()
    manifest = freeze(cases)
    diagnostics = {r['id']:r for r in read(ROOT/'endpoint_diagnostic.json')}
    rows = [validate(c,diagnostics[c['id']]) for c in cases if not c['reused_success']]
    assert not (ROOT/'physics').exists(), 'No new environment attempts authorized without feasible preflight'
    for path,digest in manifest['identities'].items():
        assert sha(path)==digest,path
    result = dict(passed=True,tests=tests.testsRun,rows=rows,shared_successes=7,actual_new_attempts=0,gains=0,
                  physical_execution_verified=False,full_path_search_completed=False,
                  promotion_allowed=False,full_48_conditions_rerun=False,
                  manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/'verification.json',result)
    print(result,flush=True)


if __name__ == '__main__':
    main()
