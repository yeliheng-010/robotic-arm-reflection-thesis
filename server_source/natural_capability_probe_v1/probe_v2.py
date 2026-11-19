from pathlib import Path
from unittest.mock import patch
import unittest
import probe
from rebuild_v2 import flow_for


def main():
    root = Path(__file__).resolve().parent
    original = probe.read(root/'manifest.json')
    assert all(probe.sha(p) == h for p, h in original['identities'].items())
    suite = unittest.defaultTestLoader.discover(str(root), pattern='test_rebuild.py')
    tests = unittest.TextTestRunner(verbosity=2).run(suite)
    assert tests.wasSuccessful()
    identities = {str(p): probe.sha(p) for p in root.iterdir() if p.suffix in ('.py', '.sbatch', '.md')}
    probe.save(root/'revision_manifest.json', dict(identities=identities, tests=tests.testsRun,
        prior_manifest_sha256=probe.sha(root/'manifest.json'), reason='approach_T2_not_nominal_T3', physical_rerun=False))
    (root/'revision_v2').mkdir(exist_ok=False)
    with patch.object(probe, 'flow_for', flow_for), patch.object(probe, 'ROOT', root/'revision_v2'):
        probe.main()
    assert all(probe.sha(p) == h for p, h in identities.items())


if __name__ == '__main__':
    main()
