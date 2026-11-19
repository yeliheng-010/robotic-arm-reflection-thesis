"""原生扩展子模块和Cython支持模块必须绑定真实二进制。"""
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from qualified_closure_dynamics_v2 import provenance


class NativeTests(unittest.TestCase):
    def setup_case(self, temp):
        root = Path(temp)
        library = root / 'lib'
        library.mkdir()
        roots = dict(project=str(root / 'project'), dependency=[str(library)], stdlib=[])
        parent = ModuleType('native')
        parent.__file__ = str(library / 'native.so')
        Path(parent.__file__).write_bytes(b'binary placeholder')
        return roots, parent

    def test_native_child_binds_extension(self):
        with tempfile.TemporaryDirectory() as t:
            roots, parent = self.setup_case(t)
            child = ModuleType('native.child')
            parent.child = child
            result = provenance.collect({'native': parent, 'native.child': child}, roots)
            self.assertIn(parent.__file__, result['modules']['native.child']['implementation_files'])

    def test_canonical_alias_uses_native_parent(self):
        with tempfile.TemporaryDirectory() as t:
            roots, parent = self.setup_case(t)
            child = ModuleType('native.child')
            parent.child = child
            result = provenance.collect({'native': parent, 'alias': child}, roots)
            self.assertEqual('native.child', result['modules']['alias']['canonical_name'])

    def test_python_wrapper_native_attribute_is_bound(self):
        with tempfile.TemporaryDirectory() as t:
            roots, native = self.setup_case(t)
            wrapper = ModuleType('wrapper')
            wrapper.__file__ = str(Path(t) / 'lib/wrapper.py')
            Path(wrapper.__file__).write_text('wrapper')
            wrapper._native = native
            child = ModuleType('wrapper.child')
            wrapper.child = child
            result = provenance.collect({'wrapper': wrapper, 'wrapper.child': child}, roots)
            self.assertIn(native.__file__, result['files'])

    def test_cython_signature_binds_contributing_binaries(self):
        with tempfile.TemporaryDirectory() as t:
            roots, parent = self.setup_case(t)
            Path(parent.__file__).write_bytes(b'prefix\0_cython_3_0_10\0suffix')
            helper = ModuleType('_cython_3_0_10')
            result = provenance.collect({'native': parent, helper.__name__: helper}, roots)
            self.assertEqual([parent.__file__], result['modules'][helper.__name__]['implementation_files'])

    def test_cython_without_binary_signature_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            roots, parent = self.setup_case(t)
            with self.assertRaises(ValueError):
                provenance.collect({'native': parent, '_cython_3_0_10': ModuleType('_cython_3_0_10')}, roots)

    def test_replaced_module_binds_class_method_source(self):
        with tempfile.TemporaryDirectory() as t:
            roots, _ = self.setup_case(t)
            source = Path(t) / 'lib/proxy.py'
            source.write_text('def init(self):\n    pass\n')
            namespace = {'__name__': 'replaced'}
            exec(compile(source.read_text(), str(source), 'exec'), namespace)
            Proxy = type('Proxy', (ModuleType,), {'__module__': 'replaced', '__init__': namespace['init']})
            proxy = Proxy()
            result = provenance.collect({'replaced': proxy}, roots)
            self.assertIn(str(source), result['files'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
