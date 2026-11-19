"""复用已验证场景和传感器；仅调整当前两个配置及外层尝试编号。"""
from contextlib import contextmanager
from unittest.mock import patch
from sd_runtime import context
from controlled.config import scenario
from diversity import runtime
from loopstudy import episode


def engine_config(config):
    result = scenario(config['seed'], 'clean')
    result['profile'].update(config['sensor'])
    result['level'] = config['group']
    return result


@contextmanager
def sensor_attempt(index):
    original = runtime.sensor_context

    def sensor(config, ignored, *, directory, trace):
        return original(config, index, directory=directory, trace=trace)

    with patch.object(runtime, 'sensor_context', sensor):
        yield


@contextmanager
def bound(config):
    original = episode.attempt

    def attempt(item, state, *, directory, index):
        with sensor_attempt(index):
            return original(item, state, directory=directory, index=index)

    with context(config), \
         patch.object(episode, 'configuration', lambda _: engine_config(config)), \
         patch.object(episode, 'attempt', attempt):
        yield
