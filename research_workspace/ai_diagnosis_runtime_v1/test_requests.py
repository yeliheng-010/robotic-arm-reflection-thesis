import json
from types import SimpleNamespace
import unittest
from test_boundary import fixture
from live_requests import build


class RequestTests(unittest.TestCase):
    def test_private_sensor_audit_and_errors_cannot_reach_prompt(self):
        ledger, record = fixture()
        record['error'] = dict(error_type='object_dropped', message='HIDDEN_CAUSE')
        sampler = SimpleNamespace(rows=[dict(observation_index=0)],
                    budget=SimpleNamespace(remaining=1), private=[dict(clean='HIDDEN_CAUSE')])
        telemetry = SimpleNamespace(public=lambda: dict(samples=[]))
        value = build(ledger, record, sampler=sampler, telemetry=telemetry, bridge=dict(planners=[]))
        text = json.dumps(value)
        self.assertNotIn('HIDDEN_CAUSE', text)
        self.assertNotIn('object_dropped', text)
        self.assertEqual(value['direct_messages'][1], value['diagnostic_messages'][1])

    def test_unavailable_command_metadata_is_not_invented(self):
        ledger, record = fixture()
        record['diagnostics'] = dict(action=None, motion_segment=None)
        sampler = SimpleNamespace(rows=[], budget=SimpleNamespace(remaining=0))
        telemetry = SimpleNamespace(public=lambda: dict(samples=[]))
        value = build(ledger, record, sampler=sampler, telemetry=telemetry, bridge=dict(planners=[]))
        fields = [r['field'] for r in value['request']['evidence']]
        self.assertNotIn('action', fields)


if __name__ == '__main__':
    unittest.main()
