"""新预检目录修复退出路径；不覆盖6689的两次失败与已有观察。"""
from unittest.mock import patch
from qualified_task_v1 import initial
from qualified_task_v1.initial import (grasp, UR5GraspEnv, VisibleSession,
    StrategySession, ReturnSession, reject_motion, ObservationComplete, observe)
from qualified_task_v1.stop import once
from qualified_task_v1.common import ROOT, RUN, verify, save, sha, read


class InitialSession(ReturnSession):
    def _engine(self):
        def capture(env):
            observe(env, self.case['config'], folder=self.folder/'initial_observation')
        render = once(capture, self.lease.defer, complete=ObservationComplete)
        with patch.object(VisibleSession, '_engine', StrategySession._engine), \
             patch.object(UR5GraspEnv, 'render', render), \
             patch.object(grasp, '_run_planners', reject_motion):
            super()._engine()


def registration():
    verify()
    paths = [ROOT/name for name in ('initial_v2.py', 'initial_v2.sbatch', 'stop.py', 'test_stop.py')]
    save(RUN/'initial_v2_manifest.json', dict(identities={str(p): sha(p) for p in paths},
        parent_sha256=sha(RUN/'manifest.json'), max_observations=2, max_task_attempts=0,
        max_model_calls=0, max_training_runs=0,
        reason='Fix reentrant finalization and early environment ownership, preserve failed 6689'))


def main():
    manifest = read(RUN/'initial_v2_manifest.json')
    assert manifest['parent_sha256'] == sha(RUN/'manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    with patch.object(initial, 'RUN', RUN/'initial_v2'), patch.object(initial, 'InitialSession', InitialSession):
        initial.main()


if __name__ == '__main__':
    import sys
    {'register': registration, 'run': main}[sys.argv[1]]()
