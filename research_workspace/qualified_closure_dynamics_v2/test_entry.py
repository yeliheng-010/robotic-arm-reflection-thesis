"""缺授权和导入失败不得消耗claim；硬阻断构造和积分。"""
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


@contextmanager
def fake_guard():
    yield dict(integration=0)


class EntryTests(unittest.TestCase):
    def test_missing_authorization_before_imports_and_claim(self):
        from qualified_closure_dynamics_v2 import entry
        with patch.dict(os.environ, SLURM_JOB_ID='test'), \
             patch.object(entry, 'verify_authorization', side_effect=FileNotFoundError('authorization')), \
             patch.object(entry, 'load_runtime') as load, patch.object(entry, 'consume') as consume:
            with self.assertRaises(FileNotFoundError):
                entry.main()
        load.assert_not_called()
        consume.assert_not_called()

    def test_import_validation_failure_precedes_claim(self):
        from qualified_closure_dynamics_v2 import entry
        with patch.dict(os.environ, SLURM_JOB_ID='test'), \
             patch.object(entry, 'verify_authorization', return_value={}), \
             patch.object(entry, 'zero_motion', fake_guard), patch.object(entry, 'load_runtime'), \
             patch.object(entry, 'read_snapshot', return_value={}), \
             patch.object(entry, 'validate_runtime', side_effect=ValueError('source changed')), \
             patch.object(entry, 'consume') as consume:
            with self.assertRaises(ValueError):
                entry.main()
        consume.assert_not_called()

    def test_old_claim_cannot_be_reused(self):
        from qualified_closure_dynamics_v2 import protocol
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):
                protocol.consume(dict(diagnostic_id='qualified_closure_dynamics_v1-978505'), Path(t))
            self.assertFalse((Path(t) / 'claim.json').exists())

    def test_duplicate_claim_rejected(self):
        from qualified_closure_dynamics_v2 import protocol
        with tempfile.TemporaryDirectory() as t, patch.object(protocol, 'sha', return_value='test'):
            auth = dict(diagnostic_id=protocol.DIAGNOSTIC_ID)
            protocol.consume(auth, Path(t))
            with self.assertRaises(FileExistsError):
                protocol.consume(auth, Path(t))

    def test_guards_block_all_construct_and_integrate_paths(self):
        from qualified_closure_dynamics_v2.guarded_imports import zero_motion
        noop = lambda *a: None
        model = SimpleNamespace(from_xml_path=noop, from_xml_string=noop, from_binary_path=noop)
        spec = SimpleNamespace(from_file=noop, from_string=noop, compile=noop)
        mj = SimpleNamespace(mj_step=noop, mj_step1=noop, mj_step2=noop, MjData=noop, MjModel=model, MjSpec=spec)
        with zero_motion(mj) as counts:
            for action in (mj.mj_step, mj.mj_step1, mj.mj_step2, mj.MjData,
                           model.from_xml_path, model.from_xml_string, model.from_binary_path,
                           spec.from_file, spec.from_string, spec.compile):
                with self.assertRaises(RuntimeError):
                    action()
        self.assertEqual(dict(integration=3, model_construction=3, data_construction=1,
                              spec_construction=3), counts)


if __name__ == '__main__':
    unittest.main(verbosity=2)
