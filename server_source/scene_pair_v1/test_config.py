"""两种场景契约；使用冻结布局，不重新生成实验数据。"""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent


class ConfigTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('pair_config'), '缺少两场景入口')
        return __import__('pair_config')

    def test_only_two_scenes_and_reject_intermediate_groups(self):
        module = self.module()
        self.assertEqual(('baseline', 'varied_noisy'), module.SCENES)
        for name in ('layout', 'appearance', 'camera', 'layout_camera', 'combined', 'mixed'):
            with self.assertRaises(ValueError):
                module.configuration(960102, name)

    def test_original_is_frozen_baseline_with_zero_noise(self):
        module = self.module()
        config = module.configuration(960102, 'baseline')
        path = ROOT.parent/'scene_diversity_v2'/'manifest.json'
        previous = json.loads(path.read_text(encoding='utf-8'))['configs']['960102_baseline']
        self.assertEqual(previous, {k: config[k] for k in previous})
        self.assertEqual(dict(depth_sigma_m=0., dropout=0.), config['sensor'])

    def test_enhanced_keeps_all_variation_and_adds_real_noise_options(self):
        config = self.module().configuration(960102, 'varied_noisy')
        self.assertTrue(config['layout_enabled'])
        self.assertEqual(7, len(config['bodies']))
        self.assertEqual(3, len(config['appearance']))
        self.assertIsNotNone(config['camera'])
        self.assertEqual(dict(depth_sigma_m=.003, dropout=.02), config['sensor'])
        self.assertTrue(config['compiled_check']['passed'])

    def test_configurations_are_isolated_and_seed_is_explicit(self):
        module = self.module()
        one = module.configuration(960102, 'varied_noisy')
        one['bodies'].clear()
        one['sensor']['dropout'] = .99
        two = module.configuration(960102, 'varied_noisy')
        self.assertEqual(7, len(two['bodies']))
        self.assertEqual(.02, two['sensor']['dropout'])
        for seed in (True, -1, 1):
            with self.assertRaises(ValueError):
                module.configuration(seed, 'baseline')


if __name__ == '__main__':
    unittest.main()
