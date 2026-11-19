"""新授权必须绑定零初始化预算和最终准备，旧授权不能复用。"""
import copy
import tempfile
import unittest
from pathlib import Path
from qualified_closure_mjb_v1.test_support import module


class ProtocolTests(unittest.TestCase):
    def prepared(self):
        p = module(self, 'protocol')
        auth = dict(execution_authorized=True, diagnostic_id=p.DIAGNOSTIC_ID,
                    budget=dict(p.BUDGET), approval_reference='explicit-test-only',
                    identities={'fixture': 'digest'}, preparation_sha256='prepared')
        return p, auth

    def test_zero_setup_bound_to_new_id(self):
        p, auth = self.prepared()
        self.assertEqual(0, p.BUDGET['setup_steps'])
        p.validate_authorization(auth, expected=auth['identities'], preparation_digest='prepared')

    def test_old_missing_or_increased_authorization_rejected(self):
        p, auth = self.prepared()
        variants = [{}, dict(auth, execution_authorized=False), dict(auth, diagnostic_id='qualified_closure_dynamics_v4-978505'),
                    dict(auth, preparation_sha256='stale'), dict(auth, approval_reference=''),
                    dict(auth, identities={'changed': 'digest'})]
        for key, value in [('setup_steps', 500), ('task_steps', 1001), ('trajectories', True)]:
            bad = copy.deepcopy(auth)
            bad['budget'][key] = value
            variants.append(bad)
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                p.validate_authorization(bad, expected=auth['identities'], preparation_digest='prepared')

    def test_second_claim_rejected(self):
        p, auth = self.prepared()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            p.consume(auth, folder, expected=auth['identities'], preparation_digest='prepared')
            with self.assertRaises(FileExistsError):
                p.consume(auth, folder, expected=auth['identities'], preparation_digest='prepared')

    def test_source_mutation_rejected(self):
        p = module(self, 'protocol')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'source'
            path.write_bytes(b'original')
            identities = {str(path): p.sha(path)}
            p.check_identities(identities)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                p.check_identities(identities)

    def test_missing_auth_before_runtime_import(self):
        from unittest.mock import patch
        entry = module(self, 'entry')
        with patch.object(entry, 'authorization', side_effect=FileNotFoundError('auth')), \
             patch.object(entry, 'execute_authorized') as execute:
            with self.assertRaises(FileNotFoundError):
                entry.main([])
        execute.assert_not_called()
