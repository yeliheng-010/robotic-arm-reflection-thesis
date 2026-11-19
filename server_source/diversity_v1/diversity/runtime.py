"""本次实验的临时注入，退出 context 后恢复原有渲染函数。"""
from contextlib import contextmanager
import hashlib
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from stability.loop_worker import engine_class
from diversity.scene import ScenarioFault
from diversity.noise import corrupt_depth


def digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


@contextmanager
def sensor_context(config, attempt, *, directory, trace):
    original = UR5GraspEnv.render
    frame = 0

    def render(env, *args, **kwargs):
        nonlocal frame
        observation = original(env, *args, **kwargs)
        seed = np.random.SeedSequence([config['seed'], 301, attempt, frame])
        noisy, stats = corrupt_depth(observation['depth'], config['profile'], seed=seed)
        stats.update(frame=frame, attempt=attempt, scene_seed=config['seed'],
                     clean_sha256=digest(observation['depth']), noisy_sha256=digest(noisy))
        trace.append(stats)
        if frame == 0:
            Path(directory).mkdir(parents=True, exist_ok=True)
            np.savez_compressed(Path(directory)/'depth_evidence.npz', clean=observation['depth'], noisy=noisy)
        frame += 1
        return {**observation, 'depth': noisy}

    with patch.object(UR5GraspEnv, 'render', render):
        yield


class DiverseEngine(engine_class()):
    def __init__(self, *, scenario_config, **kwargs):
        super().__init__(scene_jitter=0, **kwargs)
        self.scenario = scenario_config

    def _attempt(self, *args, **kwargs):
        values, trace = list(args), []
        values[3] = ScenarioFault(values[3], self.scenario)
        with sensor_context(self.scenario, values[4], directory=values[6], trace=trace):
            record, report = super()._attempt(*values, **kwargs)
        record['domain_randomization'] = {'seed': self.scenario['seed'], 'level': self.scenario['level'],
                                          'sensor_frames': trace}
        if report is not None:
            report.evidence['depth_sensor'] = {
                'sigma_m': self.scenario['profile']['depth_sigma_m'],
                'missing_probability': self.scenario['profile']['dropout'],
                'source': 'synthetic_depth_sensor', 'residuals': 'simulation_ground_truth'}
            record['error'] = report.to_dict()
        return record, report

