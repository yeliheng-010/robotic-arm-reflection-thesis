"""仅测试新增预算、一次性记录及状态掩码，不调用求解器。"""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from qualified_initial_projection_run_v2.protocol import BUDGET, RULES_SHA, claim, validate_authorization
from qualified_initial_projection_run_v2.state import check, assemble


class GateTests(unittest.TestCase):
    def auth(self):
        return dict(kind='isolated_geometry_only', geometry_execution_authorized=True,
                    dynamics_execution_authorized=False, budget=dict(BUDGET), rules_sha256=RULES_SHA)

    def fixture(self):
        names = [f'{s}_{p}_joint' for s in ('right', 'left')
                 for p in ('driver', 'coupler', 'spring_link', 'follower')]
        parameters = dict(joints=[dict(name=n, qpos_address=i, range=[-1, 1]) for i, n in enumerate(names)],
            equalities=[dict(type=2, names=['right_driver_joint', 'left_driver_joint'], data=[0, 1])])
        return np.full(30, 0.1), parameters

    def test_claim_is_exclusive(self):
        with tempfile.TemporaryDirectory() as folder:
            claim(self.auth(), folder, name='construction')
            claim(self.auth(), folder, name='right')
            with self.assertRaises(FileExistsError):
                claim(self.auth(), folder, name='right')
            with self.assertRaises(FileExistsError):
                claim(self.auth(), folder, name='construction')

    def test_side_requires_construction_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                claim(self.auth(), folder, name='left')
            self.assertFalse((Path(folder) / 'left_claim.json').exists())

    def test_unauthorized_or_dynamics_budget_rejected(self):
        for field, value in [('geometry_execution_authorized', False), ('dynamics_execution_authorized', True)]:
            auth = self.auth()
            auth[field] = value
            with self.assertRaises(ValueError):
                validate_authorization(auth)
        auth = self.auth()
        auth['budget']['integration_steps'] = 1
        with self.assertRaises(ValueError):
            validate_authorization(auth)

    def test_bool_budget_is_rejected(self):
        auth = self.auth()
        auth['budget']['attempts_per_side'] = True
        with self.assertRaises(ValueError):
            validate_authorization(auth)

    def test_allowed_passive_change_passes(self):
        source, parameters = self.fixture()
        candidate = source.copy()
        candidate[2] += 0.001
        _, contract = check(source, candidate, parameters)
        self.assertEqual([2], contract['changed_indices'])
        self.assertTrue(contract['other_state_unchanged'])

    def test_driver_or_other_state_change_rejected(self):
        source, parameters = self.fixture()
        for index in (1, 29):
            candidate = source.copy()
            candidate[index] += 1e-6
            with self.assertRaises(AssertionError):
                check(source, candidate, parameters)

    def test_change_cap_and_range_rejected(self):
        source, parameters = self.fixture()
        candidate = source.copy()
        candidate[2] += 0.011
        with self.assertRaises(ValueError):
            check(source, candidate, parameters)
        parameters['joints'][1]['range'] = [-1, 0]
        with self.assertRaises(ValueError):
            check(source, source.copy(), parameters)

    def test_driver_equality_rejected(self):
        source, parameters = self.fixture()
        source[1] += 1e-6
        with self.assertRaises(ValueError):
            check(source, source.copy(), parameters)

    def test_any_side_failure_prevents_candidate(self):
        rows = dict(right=dict(accepted=True, optimizer_success=True),
                    left=dict(accepted=False, optimizer_success=False))
        arrays, result = assemble(rows)
        self.assertIsNone(arrays)
        self.assertFalse(result['candidate_created'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
