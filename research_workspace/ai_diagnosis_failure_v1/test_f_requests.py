import json
from types import SimpleNamespace
import unittest
from test_boundary import fixture
from f_requests import build


class RequestTests(unittest.TestCase):
    def test_snapshot_excludes_future_frames_and_private_stop(self):
        ledger, record = fixture()
        record['fixture'] = {'cause': 'PRIVATE_ENGINEERING_STOP'}
        sampler = SimpleNamespace(rows=[{'observation_index': 0}], budget=SimpleNamespace(remaining=2))
        recorder = SimpleNamespace(public=lambda: {'samples': []})
        bridge = dict(grasp={'passed': True}, planners=[{'executed': True}])
        value = build(ledger, record, sampler=sampler, telemetry=recorder, bridge=bridge)
        sampler.rows.append({'observation_index': 1, 'future': 'FUTURE_FRAME'})
        encoded = json.dumps(value)
        self.assertNotIn('PRIVATE_ENGINEERING_STOP', encoded)
        self.assertNotIn('FUTURE_FRAME', encoded)
        self.assertEqual(value['direct_messages'][1], value['diagnostic_messages'][1])
        self.assertEqual(2, value['request']['budget']['observations_remaining'])
        self.assertIn('OBSERVE', [r['id'] for r in value['request']['actions']])
        self.assertIn('reset', value['request']['execution_semantics']['retry'])


if __name__ == '__main__':
    unittest.main()
