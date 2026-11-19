"""仅用假后端检验预算与停止行为，不创建MuJoCo环境。"""
import importlib
import json
import tempfile
import unittest
from pathlib import Path


class FakeBackend:
    def __init__(self, *, fault=None, at=3):
        self.steps, self.commands = 0, []
        self.fault, self.at = fault, at

    def observe(self):
        row = dict(cached_hits=[], rebuilt_hits=[], nonfinite=False,
                   warnings=False, model_changed=False)
        if self.steps == self.at and self.fault:
            row[self.fault] = [dict(hit=True)] if 'hits' in self.fault else True
        return row

    def step(self, command):
        self.commands.append(command)
        self.steps += 1


class FakeSink:
    def __init__(self, *, fail=None, at=3):
        self.fail, self.at, self.rows = fail, at, []

    def intent(self, index, command):
        if self.fail == 'intent' and index == self.at:
            raise OSError('intent write failed')
        self.rows.append(('intent', index, command))

    def observed(self, index, row):
        if self.fail == 'observed' and index == self.at:
            raise OSError('observation write failed')
        self.rows.append(('observed', index, row))


class ContractTests(unittest.TestCase):
    def module(self, name):
        try:
            return importlib.import_module('qualified_closure_dynamics_v1.' + name)
        except ModuleNotFoundError:
            self.fail('Implementation absent: ' + name)

    def run_fake(self, *, fault=None, at=3, sink=None, clock=None):
        backend = FakeBackend(fault=fault, at=at)
        report = self.module('worker').run_loop(backend, sink or FakeSink(),
                                               clock=clock or (lambda: 0.0))
        return backend, report

    def test_archived_controls_exact(self):
        controls = self.module('protocol').commands()
        path = Path(__file__).parent / 'controls.reference.json'
        self.assertEqual(json.loads(path.read_text())['control_commands'], controls)

    def test_step_zero_contact(self):
        backend, row = self.run_fake(fault='cached_hits', at=0)
        self.assertEqual(0, backend.steps)
        self.assertIn('cached_collision', row['reasons'])

    def test_raw_contact_stops_without_next_step(self):
        backend, row = self.run_fake(fault='cached_hits')
        self.assertEqual(3, backend.steps)
        self.assertIn('cached_collision', row['reasons'])

    def test_rebuilt_contact_stops_without_next_step(self):
        backend, row = self.run_fake(fault='rebuilt_hits')
        self.assertEqual(3, backend.steps)
        self.assertIn('rebuilt_collision', row['reasons'])

    def test_numeric_and_warning_and_model_change(self):
        for fault in ('nonfinite', 'warnings', 'model_changed'):
            with self.subTest(fault=fault):
                backend, row = self.run_fake(fault=fault)
                self.assertEqual(3, backend.steps)
                self.assertIn(fault, row['reasons'])

    def test_initial_numeric_failure(self):
        backend, _ = self.run_fake(fault='nonfinite', at=0)
        self.assertEqual(0, backend.steps)

    def test_full_budget_no_extra_step(self):
        backend, row = self.run_fake()
        self.assertEqual(1000, backend.steps)
        self.assertEqual('budget_exhausted', row['reasons'][0])
        self.assertEqual(self.module('protocol').commands(), backend.commands)

    def test_intent_failure_prevents_step(self):
        backend, row = self.run_fake(sink=FakeSink(fail='intent'))
        self.assertEqual(2, backend.steps)
        self.assertIn('engineering_failure', row['reasons'])
        self.assertIsNone(row['uncertain_step'])

    def test_observation_failure_no_further_step(self):
        backend, row = self.run_fake(sink=FakeSink(fail='observed'))
        self.assertEqual(3, backend.steps)
        self.assertEqual(3, row['completed_steps'])
        self.assertIn('engineering_failure', row['reasons'])

    def test_timeout_before_first_step(self):
        ticks = iter([0.0, 121.0])
        backend, row = self.run_fake(clock=lambda: next(ticks))
        self.assertEqual(0, backend.steps)
        self.assertIn('wall_timeout', row['reasons'])

    def test_failed_step_remains_uncertain(self):
        backend = FakeBackend()
        def fail(command):
            raise RuntimeError('step may have partially executed')
        backend.step = fail
        row = self.module('worker').run_loop(backend, FakeSink(), clock=lambda: 0.0)
        self.assertEqual(1, row['uncertain_step'])
        self.assertEqual(0, row['completed_steps'])

    def auth(self, folder):
        protocol = self.module('protocol')
        source = folder / 'source.txt'
        source.write_text('frozen', encoding='utf-8')
        value = dict(execution_authorized=True, approval_reference='test-only',
                     diagnostic_id=protocol.DIAGNOSTIC_ID, budget=protocol.BUDGET,
                     identities={str(source): protocol.sha(source)})
        path = folder / 'authorization.json'
        path.write_text(json.dumps(value), encoding='utf-8')
        return path, source

    def test_missing_authorization_creates_no_claim(self):
        protocol = self.module('protocol')
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with self.assertRaises((FileNotFoundError, ValueError)):
                protocol.claim(folder / 'missing.json', folder / 'run')
            self.assertFalse((folder / 'run/claim.json').exists())

    def test_second_claim_rejected(self):
        protocol = self.module('protocol')
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            auth, _ = self.auth(folder)
            protocol.claim(auth, folder / 'run')
            with self.assertRaises(FileExistsError):
                protocol.claim(auth, folder / 'run')

    def test_changed_source_rejected_before_claim(self):
        protocol = self.module('protocol')
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            auth, source = self.auth(folder)
            source.write_text('changed', encoding='utf-8')
            with self.assertRaises(ValueError):
                protocol.claim(auth, folder / 'run')
            self.assertFalse((folder / 'run/claim.json').exists())

    def test_proposed_or_extra_budget_rejected(self):
        protocol = self.module('protocol')
        for field in ('execution_authorized', 'budget'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                folder = Path(temp)
                auth, _ = self.auth(folder)
                value = json.loads(auth.read_text())
                value[field] = False if field == 'execution_authorized' else dict(task_steps=1001)
                auth.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    protocol.claim(auth, folder / 'run')


if __name__ == '__main__':
    unittest.main(verbosity=2)
