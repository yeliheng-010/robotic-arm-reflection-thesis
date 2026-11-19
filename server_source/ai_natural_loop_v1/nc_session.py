"""只在执行时暂留close；yield时恢复全局补丁，允许共享首环境与分支共存。"""
from contextlib import contextmanager
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from sd_runtime import context as scene_context
from pair_runtime import engine_config, sensor_attempt
from loopstudy.runtime import engine_class
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from guard_scope import context as guard_context
from live_motion import context as motion_context
from live_telemetry import capture
from f_lifetime import Lease
from nc_common import save, sha


class Session:
    def __init__(self, case, state, *, folder, index):
        self.case, self.state, self.folder, self.index = case, state, folder, index
        self.lease = Lease(UR5GraspEnv.close)
        self.bridge, self.guard, self.record, self.step, self.recorder = {}, {}, None, None, None

    def execute(self):
        item, config = self.case['item'], self.case['config']
        self.folder.mkdir(parents=True, exist_ok=False)
        save(self.folder/'started.json', dict(attempt_index=self.index, condition=item['id'], state=self.state))
        def defer(env):
            self.lease.defer(env)
        with scene_context(config), sensor_attempt(self.index), patch.object(UR5GraspEnv, 'close', defer), \
             capture() as recorder, motion_context(item, self.state, recorder=recorder, trace=self.bridge), \
             guard_context(item, self.guard):
            self.recorder = recorder
            self._engine()
        self.lease.mark_retained()
        self._record()

    def _engine(self):
        item = self.case['item']
        engine = engine_class(self.state)(scenario_config=engine_config(self.case['config']), max_attempts=1,
                                         headless=True, task_parser='rule')
        try:
            self.result = engine.run(source=item['source'], destination=item['destination'], seed=item['seed'],
                fault='none', output=self.folder/'execution', method='retry', context='natural-ai-closed-loop')
        finally:
            engine.close()
            save(self.folder/'bridge.json', self.bridge)
            save(self.folder/'guard.json', self.guard)
            save(self.folder/'telemetry.json', dict(stride_steps=10, rows=self.recorder.rows))

    def _record(self):
        path = self.folder/'execution/result.json'
        self.record = self.result['records'][0]
        self.step = dict(index=self.index, state=self.state, success=bool(self.result['success']),
                         result_path=str(path), result_sha256=sha(path), session_path=str(self.folder))
        save(self.folder/'step.json', self.step)

    def close(self, error):
        self.lease.state['exit_exception'] = error
        try:
            self.lease.release()
        finally:
            save(self.folder/'lifecycle.json', dict(self.lease.state, events=self.lease.events))


@contextmanager
def opened(case, state, *, folder, index):
    assert not folder.exists(), 'Never rerun an existing attempt'
    session, failure = Session(case, state, folder=folder, index=index), None
    try:
        session.execute()
        yield session
    except BaseException as error:
        failure = type(error).__name__
        raise
    finally:
        if folder.exists():
            session.close(failure)
