from types import SimpleNamespace
from copy import deepcopy
import unittest
from test_boundary import fixture
from live_requests import build as old_build
from live_requests_v2 import build


class RevisionTests(unittest.TestCase):
    def test_original_rejects_executor_tuple_fixed_adapter_preserves_values(self):
        ledger, record = fixture()
        args = dict(sampler=SimpleNamespace(rows=[], budget=SimpleNamespace(remaining=0)),
                    telemetry=SimpleNamespace(public=lambda: dict(samples=[])), bridge=dict(planners=[]))
        expected = old_build(ledger, record, **args)
        record = deepcopy(record)
        for name in ('grasp_offset', 'place_offset'):
            record['parameters'][name] = tuple(record['parameters'][name])
        with self.assertRaisesRegex(ValueError, 'Bad command vector'):
            old_build(ledger, record, **args)
        self.assertEqual(expected, build(ledger, record, **args))
        self.assertIsInstance(record['parameters']['grasp_offset'], tuple)


if __name__ == '__main__':
    unittest.main()
