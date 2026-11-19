"""新执行入口：初态检查与每次暂停观测检查，失败不向下游发布。"""
from unittest.mock import patch
import numpy as np
from cv_select import evaluate
from cv_policy import REQUIRED
from sd_inventory import root_boxes
from reflection.sim_sensing import SegmentationRenderer
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from live_observations import Sampler, state
from top_session import StrategySession
from cc_common import save, sha
from cc_policy import guarded_capture


def live_report(env, config, *, path):
    before = state(env)
    renderer = SegmentationRenderer(env.mj_model, env.height, env.width)
    try:
        boxes = root_boxes(env.mj_model, env.mj_data)
        result = evaluate(env, renderer, config['camera'], boxes={n: boxes[n] for n in REQUIRED})
        np.testing.assert_array_equal(before, state(env))
    finally:
        renderer.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = path.with_suffix('.npz')
    with snapshot.open('xb') as stream:
        np.savez_compressed(stream, state=before)
    result.update(state_path=str(snapshot), state_sha256=sha(snapshot), state_unchanged=True)
    save(path, result)
    return result


class GuardedSampler(Sampler):
    def capture(self):
        if self.config['group'] == 'baseline':
            return super().capture()
        def check():
            path = self.folder/f'visibility_{self.budget.count}.json'
            return live_report(self.env, self.config, path=path)
        return guarded_capture(check, super().capture)


class VisibleSession(StrategySession):
    def _engine(self):
        if self.case['config']['group'] == 'baseline':
            return super()._engine()
        original, seen = UR5GraspEnv.render, set()
        def render(env):
            if id(env) in seen:
                return original(env)
            def check():
                with patch.object(UR5GraspEnv, 'render', original):
                    return live_report(env, self.case['config'], path=self.folder/'initial_visibility.json')
            result = guarded_capture(check, lambda: original(env))
            seen.add(id(env))
            return result
        with patch.object(UR5GraspEnv, 'render', render):
            super()._engine()
