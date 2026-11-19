"""补登记只能使用已复核的明确文件，变更和越界仍拒绝。"""
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import sha


class ReviewedTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module('qualified_closure_dynamics_v3.source_review')
        except ModuleNotFoundError:
            self.fail('Reviewed source binding implementation absent')

    def fixture(self, folder, *, reviewed=True):
        source = folder / 'existing.py'
        source.write_text('existing')
        path = folder / 'review.json'
        path.write_text(json.dumps(dict(reviewed=reviewed, scope='new_binding_current_state',
                                       identities={str(source): sha(source)})))
        return path, source

    def test_reviewed_matching_file_accepted(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as t:
            path, source = self.fixture(Path(t))
            self.assertEqual({str(source): sha(source)}, module.load(path, Path(t)))

    def test_unreviewed_inventory_rejected(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as t:
            path, _ = self.fixture(Path(t), reviewed=False)
            with self.assertRaises(ValueError):
                module.load(path, Path(t))

    def test_changed_file_rejected(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as t:
            path, source = self.fixture(Path(t))
            source.write_text('changed')
            with self.assertRaises(ValueError):
                module.load(path, Path(t))

    def test_outside_project_rejected(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as t:
            path, _ = self.fixture(Path(t))
            with self.assertRaises(ValueError):
                module.load(path, Path(t) / 'project')


if __name__ == '__main__':
    unittest.main(verbosity=2)
