"""异常展开时记录实际关闭完成；close失败不得伪报released。"""
from contextlib import contextmanager
from unittest.mock import patch
from f_common import save


class Lease:
    def __init__(self, original):
        self.original, self.env = original, None
        self.events = []
        self.state = dict(environment_retained=False, retained_after_attempt=False, released=False,
                          close_requests=0, actual_close_calls=0, exit_exception=None, close_error=None)

    def defer(self, env):
        if self.env is not None and self.env is not env:
            self.original(env)
            raise RuntimeError('Unexpected second environment')
        self.env = env
        self.state['environment_retained'] = True
        self.state['close_requests'] += 1
        self.events.append('close_deferred')

    def mark_retained(self):
        assert self.env is not None and self.state['close_requests'] >= 1
        assert not self.state['released']
        self.state['retained_after_attempt'] = True
        self.events.append('retained_for_observation')

    def release(self):
        if self.env is None or self.state['released']:
            return
        self.events.append('close_started')
        self.state['actual_close_calls'] += 1
        try:
            self.original(self.env)
        except BaseException as error:
            self.state['close_error'] = type(error).__name__
            self.events.append('close_failed')
            raise
        self.state['released'] = True
        self.events.append('close_completed')


@contextmanager
def managed(env_type, folder):
    lease = Lease(env_type.close)
    def defer(env):
        lease.defer(env)
    try:
        with patch.object(env_type, 'close', defer):
            yield lease
    except BaseException as error:
        lease.state['exit_exception'] = type(error).__name__
        lease.events.append('exception_unwind')
        raise
    finally:
        try:
            lease.release()
        finally:
            save(folder/'lifecycle.json', dict(lease.state, events=lease.events))
