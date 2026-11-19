"""GPU准备与执行入口回归；使用假数据，不导入仿真。"""
import unittest
from unittest.mock import patch
from qualified_closure_dynamics_v4 import runtime, entry


class GpuEntryTests(unittest.TestCase):
    def profile(self):
        return dict(slurm=True, gpu_allocated=True, torch_devices=1,
                    open3d_devices=1, open3d_backend='cuda')

    def test_cpu_allocation_rejected(self):
        profile = self.profile()
        profile['gpu_allocated'] = False
        with self.assertRaises(ValueError):
            runtime.require_gpu(profile)

    def test_cpu_open3d_backend_rejected(self):
        profile = self.profile()
        profile['open3d_backend'] = 'cpu'
        with self.assertRaises(ValueError):
            runtime.require_gpu(profile)

    def test_missing_devices_rejected(self):
        for key in ('torch_devices', 'open3d_devices'):
            with self.subTest(key=key):
                profile = self.profile()
                profile[key] = 0
                with self.assertRaises(ValueError):
                    runtime.require_gpu(profile)

    def test_gpu_profile_accepted(self):
        self.assertIsNone(runtime.require_gpu(self.profile()))

    def test_probe_never_enters_authorization_or_execution(self):
        with patch.object(entry, 'inspect_entry') as inspect, patch.object(entry, 'execute') as execute:
            entry.main(['--verify-imports'])
        inspect.assert_called_once_with()
        execute.assert_not_called()

    def test_unknown_option_fails_closed(self):
        with patch.object(entry, 'inspect_entry') as inspect, patch.object(entry, 'execute') as execute:
            with self.assertRaises(ValueError):
                entry.main(['--verify-import'])
        inspect.assert_not_called()
        execute.assert_not_called()

    def test_execution_requires_authorization_before_claim(self):
        with patch.object(entry, 'preclaim', side_effect=ValueError('No authorization')):
            with patch.object(entry, 'consume') as consume:
                with self.assertRaisesRegex(ValueError, 'No authorization'):
                    entry.main([])
        consume.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
