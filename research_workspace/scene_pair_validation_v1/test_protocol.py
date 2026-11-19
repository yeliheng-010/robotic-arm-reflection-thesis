"""新验证不得引入中间场景或改变完整分母。"""
import importlib.util
import unittest


class ProtocolTests(unittest.TestCase):
    def test_exact_pairing_and_no_intermediate_scene(self):
        self.assertIsNotNone(importlib.util.find_spec('pv_protocol'), '缺少配对验证协议')
        import pv_protocol as module
        rows = module.items()
        self.assertEqual(48, len(rows))
        self.assertEqual(48, len({row['id'] for row in rows}))
        self.assertEqual({'baseline', 'varied_noisy'}, {row['group'] for row in rows})
        for seed in module.SEEDS:
            group = [row for row in rows if row['seed'] == seed]
            self.assertEqual(4, len(group))
            self.assertTrue(all(row['split'] == 'new_seed_development_validation' for row in group))


if __name__ == '__main__':
    unittest.main()
