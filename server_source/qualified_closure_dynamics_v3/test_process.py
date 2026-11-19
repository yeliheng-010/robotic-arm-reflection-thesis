"""主进程别名仅在对象身份及明确入口白名单均匹配时归一。"""
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from qualified_closure_dynamics_v3 import provenance
from qualified_closure_dynamics_v1.protocol import sha


class ProcessTests(unittest.TestCase):
    def fixture(self, temp):
        root = Path(temp)
        main = ModuleType('__main__')
        main.__file__ = str(root / 'entry.py')
        Path(main.__file__).write_text('entry')
        roots = dict(project=str(root), dependency=[], stdlib=[])
        return main, roots, {main.__file__: sha(Path(main.__file__))}

    def test_real_main_alias_is_not_an_ordinary_module(self):
        with tempfile.TemporaryDirectory() as t:
            main, roots, _ = self.fixture(t)
            result = provenance.collect({'__main__': main, '__mp_main__': main}, roots)
            self.assertNotIn('__mp_main__', result['modules'])

    def test_entrypoint_is_explicitly_bound(self):
        self.assertTrue(hasattr(provenance, 'verify_entrypoint'), 'Entrypoint identity verification absent')
        with tempfile.TemporaryDirectory() as t:
            main, _, allowed = self.fixture(t)
            modules = {'__main__': main, '__mp_main__': main}
            self.assertEqual(main.__file__, provenance.verify_entrypoint(modules, allowed)['file'])
            with self.assertRaises(ValueError):
                provenance.verify_entrypoint(modules, {})
            Path(main.__file__).write_text('changed')
            with self.assertRaises(ValueError):
                provenance.verify_entrypoint(modules, allowed)

    def test_same_name_without_alias_identity_is_bound_normally(self):
        with tempfile.TemporaryDirectory() as t:
            main, roots, _ = self.fixture(t)
            other = ModuleType('__mp_main__')
            other.__file__ = str(Path(t) / 'other.py')
            Path(other.__file__).write_text('other')
            result = provenance.collect({'__main__': main, '__mp_main__': other}, roots)
            self.assertIn('__mp_main__', result['modules'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
