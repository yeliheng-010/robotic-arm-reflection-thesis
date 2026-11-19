from pathlib import Path
from unittest.mock import patch
import unittest
import probe
from rebuild_v3 import flow_for, joints


def main():
    root = Path(__file__).resolve().parent
    revision = probe.read(root/'revision_manifest.json')
    assert all(probe.sha(p) == h for p, h in revision['identities'].items())
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(root)))
    assert tests.wasSuccessful()
    manifest = probe.verify()
    audited = probe.read(probe.SOURCE/f'audit_{probe.SEED}.json')
    cases = [c for c in manifest['cases'] if c['item']['seed']==probe.SEED and c['item']['group']=='varied_noisy']
    identities = {str(p): probe.sha(p) for p in root.iterdir() if p.suffix in ('.py', '.md', '.sbatch')}
    probe.save(root/'revision_v3_manifest.json', dict(identities=identities, tests=tests.testsRun,
        prior_revision_sha256=probe.sha(root/'revision_manifest.json'), reason='optional_prepose_q1'))
    first = root/'revision_v2'/(cases[0]['item']['id']+'_plan.json')
    old = probe.read(first)
    step, bridge = probe.previous(cases[0], audited)
    joints(bridge, probe.read(step['result_path'])['records'][0]['approach_plan'])
    rows = [dict(id=cases[0]['item']['id'], status=old['status'], endpoint_passing=old['endpoints']['passing'],
        selected=(old['selected'] or {}).get('id'), reused_static_result=True, plan_sha256=probe.sha(first))]
    with patch.object(probe, 'flow_for', flow_for), patch.object(probe, 'ROOT', root/'revision_v3'):
        rows.append(probe.inspect(cases[1], audited))
    assert all(probe.sha(p) == h for p, h in identities.items())
    probe.save(root/'result_v3.json', dict(rows=rows, physical_attempts=0, model_calls=0, training_runs=0))
    print({r['id']: r['status'] for r in rows}, flush=True)


if __name__ == '__main__':
    main()
