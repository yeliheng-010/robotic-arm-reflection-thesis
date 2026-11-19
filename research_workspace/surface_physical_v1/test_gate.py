import tempfile
import unittest
from pathlib import Path
from surface_grasp_v1.common import save,sha
from surface_physical_v1.gate import claim


def trial(root, *, passed=True):
    root=Path(root)
    save(root/'manifest.json',dict(identities={},max_attempts=1))
    save(root/'preflight_result.json',dict(passed=passed))
    save(root/'preflight_audit.json',dict(passed=passed,independent=True))
    identities={str(p):sha(p) for p in root.glob('*.json')}
    save(root/'execution_manifest.json',dict(identities=identities,max_physical_attempts=1))
    return root


class GateTests(unittest.TestCase):
    def test_success_consumes_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root=trial(folder)
            claim(root)
            self.assertTrue((root/'attempt_claim.json').exists())
            with self.assertRaises(FileExistsError):
                claim(root)

    def test_failed_preflight_consumes_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=trial(folder,passed=False)
            with self.assertRaises(AssertionError):
                claim(root)
            self.assertFalse((root/'attempt_claim.json').exists())

    def test_modified_preflight_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            root=trial(folder)
            (root/'preflight_result.json').write_text('{"passed":true,"changed":true}')
            with self.assertRaises(AssertionError):
                claim(root)
            self.assertFalse((root/'attempt_claim.json').exists())

    def test_existing_attempt_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            root=trial(folder)
            (root/'cases').mkdir()
            with self.assertRaises(AssertionError):
                claim(root)
            self.assertFalse((root/'attempt_claim.json').exists())
