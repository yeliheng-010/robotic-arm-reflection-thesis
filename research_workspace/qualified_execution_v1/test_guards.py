import ast
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from qualified_execution_v1 import register
from qualified_execution_v1.common import save, sha


def backend_fixture(feasible):
    source = Path(__file__).with_name('runtime.py')
    node = next(n for n in ast.parse(source.read_text(encoding='utf-8')).body
        if isinstance(n, ast.ClassDef) and n.name == 'GuardedBackend')
    def abort(*args, **kwargs):
        raise RuntimeError('guard_rejected')
    scope = dict(clone_robot=lambda r: r, robot_context=lambda *a: {}, plan_values=lambda s: [],
        compare=lambda *a: {}, held_check=lambda *a, **k: dict(feasible=feasible),
        monitors=SimpleNamespace(abort=abort, ErrorType=SimpleNamespace(COLLISION=1)))
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), scope)
    cls = scope['GuardedBackend']
    obj = object.__new__(cls)
    obj.phase, obj.expected_carry, obj.trace = 'carry', [('lift', None, 1.)], []
    obj.flow, obj.case = SimpleNamespace(T_wo=None), dict(item={})
    return obj


class GuardTests(unittest.TestCase):
    def test_failed_live_path_never_executes(self):
        backend, called = backend_fixture(False), []
        backend.original = lambda *a: called.append(True)
        env = SimpleNamespace(mj_data=SimpleNamespace(time=0.))
        with self.assertRaisesRegex(RuntimeError, 'guard_rejected'):
            backend.run(None, env, [None], [0., 1.], None, .002)
        self.assertEqual([], called)
        self.assertFalse(backend.trace[0]['executed'])

    def test_approved_live_path_executes_once(self):
        backend, called = backend_fixture(True), []
        backend.original = lambda *a: called.append(True)
        env = SimpleNamespace(mj_data=SimpleNamespace(time=0.))
        backend.run(None, env, [None], [0., 1.], None, .002)
        self.assertEqual([True], called)

    def test_claim_is_single_use_and_inputs_frozen(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'source.txt'
            source.write_text('frozen')
            save(root/'execution_manifest.json', dict(max_physical_attempts=1, identities={str(source): sha(source)}))
            with patch.object(register, 'RUN', root), patch.object(register, 'verify', lambda: {}):
                register.claim()
                with self.assertRaises(FileExistsError):
                    register.claim()
                source.write_text('changed')
                with self.assertRaises(AssertionError):
                    register.claim()


if __name__ == '__main__':
    unittest.main()
