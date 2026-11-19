import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
import unittest
from unittest.mock import patch


class SourceTests(unittest.TestCase):
    def setUp(self):
        name = 'qualified_prompt_checkpoint_v2.provenance'
        self.assertIsNotNone(importlib.util.find_spec(name), 'missing virtual-module source filter')
        self.module = __import__(name, fromlist=['provenance'])

    def sample(self, path, name):
        module = ModuleType(name)
        module.__file__ = str(path)
        return module

    def test_inherited_virtual_file_attribute_matches_real_torch_shape(self):
        class Virtual(ModuleType):
            __file__ = '_classes.py'
        module = Virtual('torch.classes')
        self.assertNotIn('__file__', vars(module))
        result = self.module.loaded_project_sources(dict(identities={}), modules={'torch.classes': module})
        self.assertEqual({}, result['sources'])
        self.assertEqual('_classes.py', result['virtual_modules'][0]['raw_file'])

    def test_virtual_torch_names_are_recorded_not_mistaken_for_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'source.py'
            path.write_text('value = 1\n', encoding='utf-8')
            modules = {'real': self.sample(path, 'real'),
                       'torch.classes': self.sample('_classes.py', 'torch.classes'),
                       'torch.ops': self.sample('_ops.py', 'torch.ops')}
            expected = {str(path): self.module.sha(path)}
            with patch.object(self.module, 'PROJECT', root):
                result = self.module.loaded_project_sources(dict(identities=expected), modules=modules)
            self.assertEqual(expected, result['sources'])
            self.assertEqual(['torch.classes', 'torch.ops'], [r['module'] for r in result['virtual_modules']])

    def test_real_unknown_or_changed_project_source_still_fails(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'source.py'
            path.write_text('value = 1\n', encoding='utf-8')
            modules = {'real': self.sample(path, 'real')}
            with patch.object(self.module, 'PROJECT', root):
                for identities in ({}, {str(path): 'incorrect'}):
                    with self.assertRaises(AssertionError):
                        self.module.loaded_project_sources(dict(identities=identities), modules=modules)

    def test_missing_real_source_is_not_silently_excluded(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'missing.py'
            modules = {'real': self.sample(path, 'real')}
            with patch.object(self.module, 'PROJECT', root), self.assertRaises(AssertionError):
                self.module.loaded_project_sources(dict(identities={str(path): 'missing'}), modules=modules)


if __name__ == '__main__':
    unittest.main()
