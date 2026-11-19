import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
import unittest


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        name = 'qualified_checkpoint_preflight_v1.protocol'
        self.assertIsNotNone(importlib.util.find_spec(name), 'missing fixed-action static protocol')
        self.module = __import__(name, fromlist=['protocol'])

    def fixture(self, root):
        inputs = root / 'input.json'
        self.module.save(inputs, dict(action={'id': 'PROPOSE_GRASP', 'args': {}}, source='frozen'))
        self.module.save(root / 'manifest.json', dict(max_preflight_sessions=1, max_audit_replays=1,
            max_model_calls=0, max_physical_attempts=0, max_training_runs=0,
            identities={str(inputs): self.module.sha(inputs)}, input_sha256=self.module.sha(inputs)))

    def test_preflight_claim_is_exclusive_even_with_concurrent_requests(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            def reserve(_):
                try:
                    self.module.reserve(root)
                    return True
                except FileExistsError:
                    return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(1, sum(pool.map(reserve, (1, 2))))
            with self.assertRaises(FileExistsError):
                self.module.reserve(root)
            self.assertEqual(1, self.module.read(root / 'preflight_claim.json')['consumed'])

    def test_changed_input_rejected_before_claim(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / 'input.json').write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                self.module.reserve(root)
            self.assertFalse((root / 'preflight_claim.json').exists())

    def test_any_extra_model_or_physical_budget_rejected(self):
        for key in ('max_model_calls', 'max_physical_attempts', 'max_training_runs', 'max_preflight_sessions'):
            with TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root)
                manifest = self.module.read(root / 'manifest.json')
                manifest[key] += 1
                (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaises(ValueError):
                    self.module.reserve(root)

    def test_source_requires_audited_novel_action_equal_to_raw_response(self):
        project = Path(__file__).resolve().parent.parent
        source = project / 'qualified_prompt_checkpoint_v2/run'
        action = self.module.source_action(source)
        self.assertEqual(dict(id='PROPOSE_GRASP', args=dict(region='center', depth_mm=15,
            tilt_deg=30, azimuth_deg=135, symmetry_deg=180)), action)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('result.json', 'response.json', 'audit_result.json', 'request.json'):
                value = self.module.read(source / name)
                if name == 'result.json':
                    value['action']['args']['depth_mm'] = 20
                self.module.save(root / name, value)
            with self.assertRaises(ValueError):
                self.module.source_action(root)


if __name__ == '__main__':
    unittest.main()
