"""单进程尝试拥有环境；原引擎请求关闭时暂留，退出必定释放。"""
from contextlib import contextmanager
from unittest.mock import patch


class Lease:
    def __init__(self, original):
        self.original, self.env = original, None
        self.close_requests, self.released = 0, False

    def defer(self, env):
        if self.env is not None and self.env is not env:
            self.original(env)
            raise RuntimeError('More than one environment in a single attempt')
        self.env = env
        self.close_requests += 1

    def release(self):
        if self.env is not None and not self.released:
            self.released = True
            self.original(self.env)


@contextmanager
def retained(env_type):
    lease = Lease(env_type.close)
    def defer(env):
        lease.defer(env)
    try:
        with patch.object(env_type, 'close', defer):
            yield lease
    finally:
        lease.release()
