"""测试进程禁止真实积分，记录阻断计数，不创建场景。"""
import unittest
from contextlib import ExitStack
from unittest.mock import patch
from qualified_closure_dynamics_v1.protocol import ROOT


def main():
    from reflection.__main__ import bootstrap
    bootstrap()
    import mujoco
    from qualified_execution_v1 import environment
    calls = []
    def forbid(*args, **kwargs):
        calls.append(1)
        raise AssertionError('Real simulation/scene forbidden in preparation tests')
    with ExitStack() as stack:
        for name in ('mj_step', 'mj_step1', 'mj_step2'):
            stack.enter_context(patch.object(mujoco, name, forbid))
        stack.enter_context(patch.object(environment, 'scene', forbid))
        suite = unittest.defaultTestLoader.discover(str(ROOT), pattern='test_*.py')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(dict(real_integration_or_scene_requests=len(calls), actual_integration_steps=0), flush=True)
    if not result.wasSuccessful() or calls:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
