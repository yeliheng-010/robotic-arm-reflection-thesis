"""完整轨迹审计必须拒绝不确定、缺记录、错误控制及停止后积分。"""
import json
import tempfile
import unittest
from pathlib import Path
from qualified_closure_mjb_v1.test_support import module, trace


def rewrite(path, **changes):
    value = json.loads(path.read_text())
    value.update(changes)
    path.write_text(json.dumps(value))


class AuditTests(unittest.TestCase):
    def test_zero_setup_valid_trace(self):
        audit = module(self, 'trace')
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            trace(folder)
            self.assertEqual(2, audit.trace_contract(folder))

    def test_old_setup_uncertain_and_missing_completion_rejected(self):
        audit = module(self, 'trace')
        for change in (dict(setup_steps=500), dict(uncertain_step=3), dict(task_step_returns=1),
                       dict(observed_steps=1), dict(error='failure')):
            with tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                trace(folder)
                rewrite(folder/'result.json', **change)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    audit.trace_contract(folder)

    def test_wrong_control_or_stop_before_last_rejected(self):
        audit = module(self, 'trace')
        for filename, change in [('intent_0001.json', dict(gripper_command=2)),
                                 ('observed_0001.json', dict(cached_hits=['early']))]:
            with tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                trace(folder)
                rewrite(folder/filename, **change)
                with self.assertRaises(ValueError):
                    audit.trace_contract(folder)

    def test_extra_intent_or_missing_state_rejected(self):
        audit = module(self, 'trace')
        for extra in (True, False):
            with tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                trace(folder)
                if extra:
                    (folder/'intent_0003.json').write_text('{}')
                else:
                    (folder/'state_0001.npz').rename(folder/'missing.fixture')
                with self.assertRaises(ValueError):
                    audit.trace_contract(folder)
