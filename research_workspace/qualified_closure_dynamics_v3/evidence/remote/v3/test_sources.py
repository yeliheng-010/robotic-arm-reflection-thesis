"""来源分类与证据变更回归；只操作临时文本，不创建仿真。"""
import importlib
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace


class SourceTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module('qualified_closure_dynamics_v3.provenance')
        except ModuleNotFoundError:
            self.fail('Source classifier implementation absent')

    def fixture(self, temp):
        root = Path(temp)
        project, library, stdlib = root / 'project', root / 'project/env/lib/site-packages', root / 'stdlib'
        for p in (project, library, stdlib):
            p.mkdir(parents=True, exist_ok=True)
        return dict(project=str(project), dependency=[str(library)], stdlib=[str(stdlib)])

    def file(self, name):
        path = Path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('x = 1\n', encoding='utf-8')
        return path

    def test_nested_dependency_precedes_project(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as t:
            roots = self.fixture(t)
            p = self.file(Path(roots['dependency'][0]) / '_distutils_hack/__init__.py')
            self.assertEqual('dependency', m.classify(p, roots))

    def test_project_named_site_packages_is_still_project(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as t:
            roots = self.fixture(t)
            p = self.file(Path(roots['project']) / 'site-packages/own.py')
            self.assertEqual('project', m.classify(p, roots))

    def test_stdlib_classification(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as t:
            roots = self.fixture(t)
            self.assertEqual('stdlib', m.classify(self.file(Path(roots['stdlib'][0]) / 'abc.py'), roots))

    def test_symlink_escape_is_not_trusted(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as t:
            roots = self.fixture(t)
            outside = self.file(Path(t) / 'outside.py')
            link = Path(roots['dependency'][0]) / 'linked.py'
            link.symlink_to(outside)
            with self.assertRaises(ValueError):
                m.classify(link, roots)

    def test_symlink_to_dependency_records_real_category(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as t:
            roots = self.fixture(t)
            actual = self.file(Path(roots['dependency'][0]) / 'real.py')
            link = Path(roots['project']) / 'alias.py'
            link.symlink_to(actual)
            self.assertEqual('dependency', m.classify(link, roots))

    def test_path_traversal_does_not_bypass_roots(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as t:
            roots = self.fixture(t)
            self.file(Path(t) / 'outside.py')
            with self.assertRaises(ValueError):
                m.classify(Path(roots['project']) / '../outside.py', roots)

    def test_missing_real_module_is_rejected(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as t:
            roots = self.fixture(t)
            module = ModuleType('missing')
            module.__file__ = str(Path(roots['project']) / 'missing.py')
            with self.assertRaises(ValueError):
                m.collect({'missing': module}, roots)

    def test_virtual_proxy_binds_implementation(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as t:
            roots = self.fixture(t)
            source = ModuleType('proxy_code')
            source.__file__ = str(self.file(Path(roots['dependency'][0]) / 'proxy_code.py'))
            Proxy = type('Proxy', (), {'__module__': 'proxy_code'})
            proxy = Proxy()
            proxy.__file__ = '_classes.py'
            result = m.collect({'proxy_code': source, 'proxy': proxy}, roots)
            self.assertEqual('proxy_code', result['modules']['proxy']['implementation_module'])
            self.assertIn(source.__file__, result['files'])

    def test_virtual_proxy_without_bound_implementation_rejected(self):
        m = self.module()
        with tempfile.TemporaryDirectory() as t:
            roots = self.fixture(t)
            Proxy = type('Proxy', (), {'__module__': 'unbound_proxy'})
            with self.assertRaises(ValueError):
                m.collect({'proxy': Proxy()}, roots)

    def test_project_and_dependency_tampering_rejected(self):
        m = self.module()
        for category in ('project', 'dependency'):
            with self.subTest(category=category), tempfile.TemporaryDirectory() as t:
                roots = self.fixture(t)
                folder = roots['project'] if category == 'project' else roots['dependency'][0]
                module = ModuleType('real')
                module.__file__ = str(self.file(Path(folder) / 'real.py'))
                result = m.collect({'real': module}, roots)
                Path(module.__file__).write_text('changed')
                with self.assertRaises(ValueError):
                    m.verify_files(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
