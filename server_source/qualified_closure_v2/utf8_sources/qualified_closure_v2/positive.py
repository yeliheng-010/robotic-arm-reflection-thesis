"""张开初态上方构型的安全对照，不冒充成功抓取或执行物理动作。"""
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from qualified_execution_v1.environment import opened
from qualified_execution_v1.common import case
from qualified_execution_v1 import runtime
from qualified_task_v1.integrity import fingerprint, unchanged
from routecheck.clone import clone_robot
from qualified_closure_v2.common import ROOT, RUN, save, sha, verify
from qualified_closure_v2.adapter import instrument
from qualified_closure_v2.geometry import sweep


def main():
    verify()
    sources = {str(ROOT / name): sha(ROOT / name) for name in ('positive.py', 'positive.sbatch')}
    save(RUN / 'positive_manifest.json', dict(sources=sources, physical_budget=0))
    item, calls = case(), []
    with opened(item, {}, static=True) as env:
        before = fingerprint(env)
        flow = SimpleNamespace(env=env, robot=clone_robot(env.robot))
        def sentinel(value, *, loops):
            calls.append(loops)
            return 'safe_sentinel_only'
        with patch.object(runtime.grasp.GraspFlow, 'close_gripper', sentinel):
            with instrument(item['item'], folder=RUN / 'safe_home_test'):
                returned = runtime.grasp.GraspFlow.close_gripper(flow, loops=17)
        assert returned == 'safe_sentinel_only' and calls == [17]
        for command, count in (([float('nan')] * 6, 81), ([0.] * 6, 1)):
            try:
                sweep(env, item['item'], command=command, sample_count=count)
            except ValueError:
                pass
            else:
                raise AssertionError('Malformed input was accepted')
        isolation = unchanged(before, fingerprint(env))
    verify()
    assert all(sha(name) == value for name, value in sources.items())
    result = dict(passed=True, case='safe_home_geometry_only_not_grasp',
                  guarded_original_sentinel_calls=len(calls), physical_close_calls=0,
                  invalid_inputs_rejected=2, isolation=isolation,
                  physical_attempts=0, model_calls=0, training_runs=0)
    save(RUN / 'positive.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
