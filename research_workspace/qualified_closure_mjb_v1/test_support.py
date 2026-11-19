"""新增入口测试的纯替身与模块存在性断言。"""
import importlib
import importlib.util
from qualified_closure_dynamics_v1.protocol import save


def module(test, name):
    full = 'qualified_closure_mjb_v1.'+name
    test.assertIsNotNone(importlib.util.find_spec(full), 'Missing implementation: '+name)
    return importlib.import_module(full)


def clean():
    return dict(cached_hits=[], rebuilt_hits=[], nonfinite=False, warnings=False,
                model_changed=False, initial_rejections=[])


class Backend:
    def __init__(self, *, stop=None, at=2, error=False):
        self.count, self.stop, self.at, self.error = 0, stop, at, error

    def observe(self):
        row = clean()
        if self.stop and self.count == self.at:
            row[self.stop] = ['hit'] if self.stop.endswith('_hits') else True
        return row

    def step(self, command):
        self.count += 1
        if self.error:
            raise RuntimeError('native failure')


class Sink:
    def __init__(self, *, fail=None):
        self.fail, self.intents, self.observations = fail, [], []

    def intent(self, index, command):
        if self.fail == 'intent':
            raise OSError('intent failed')
        self.intents.append((index, command))

    def observed(self, index, row):
        if self.fail == 'observed' and index:
            raise OSError('state write failed')
        self.observations.append(index)


def trace(folder, *, count=2):
    from qualified_closure_dynamics_v1.protocol import commands
    save(folder/'result.json', dict(completed_steps=count, uncertain_step=None, error=None,
         reasons=['cached_collision'], setup_steps=0, task_step_requests=count,
         task_step_returns=count, observed_steps=count))
    for index in range(count+1):
        row = clean()
        if index == count:
            row['cached_hits'] = ['hit']
        save(folder/f'observed_{index:04d}.json', dict(step=index, task_steps=index, **row))
        (folder/f'state_{index:04d}.npz').write_bytes(b'trace fixture, not numerical state')
        if index:
            save(folder/f'intent_{index:04d}.json', dict(step=index, gripper_command=commands()[index-1]))
