"""冻结矩阵与来源边界验证，不执行模拟器。"""
import unittest
from collections import Counter
from pilot_common import scenes, source_seeds, SEEDS, MAX_PHYSICAL
from policy import MAX_ATTEMPTS, MAX_ALTERNATIVES


class DesignTests(unittest.TestCase):
    def test_train_only_and_new_seeds(self):
        rows = scenes()
        self.assertEqual(24, len(rows))
        self.assertEqual(24, len({r['id'] for r in rows}))
        self.assertTrue(all(r['split'] == 'train_candidate' for r in rows))
        self.assertFalse(set(SEEDS) & source_seeds())

    def test_balanced_noises_and_families(self):
        rows = scenes()
        self.assertEqual({i:4 for i in range(6)}, dict(Counter(r['noise_index'] for r in rows)))
        self.assertEqual({'grasp_collision':12, 'grasp_place':12}, dict(Counter(r['factor'] for r in rows)))

    def test_execution_budget(self):
        qualification = 2
        baseline_new = MAX_ATTEMPTS-1
        alternatives_new = sum(MAX_ALTERNATIVES*(MAX_ATTEMPTS-i) for i in range(1, MAX_ATTEMPTS))
        self.assertEqual(MAX_PHYSICAL, qualification+baseline_new+alternatives_new)

    def test_all_modules_import(self):
        import worker
        import audit
        import labels
        import report
        import run
        self.assertTrue(callable(audit.audit_trace))


if __name__ == '__main__':
    unittest.main()
