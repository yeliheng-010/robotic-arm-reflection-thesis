"""实际执行入口首次render处采集，禁止继续感知或执行任务规划。"""
import os
import traceback
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import nc_session
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from cc_runtime import VisibleSession
from top_session import StrategySession
from rh_runtime import ReturnSession
from qa_runtime import reject_motion
from qualified_task_v1.observer import observe, ObservationRejected
from qualified_task_v1.common import RUN, PILOT, verify, read, save


class ObservationComplete(BaseException):
    pass


class InitialSession(ReturnSession):
    def _engine(self):
        def render(env):
            observe(env, self.case['config'], folder=self.folder/'initial_observation')
            raise ObservationComplete()
        with patch.object(VisibleSession, '_engine', StrategySession._engine), \
             patch.object(UR5GraspEnv, 'render', render), \
             patch.object(grasp, '_run_planners', reject_motion):
            super()._engine()


def main():
    manifest = verify()
    seed = PILOT[int(os.environ['SLURM_ARRAY_TASK_ID'])]
    case, folder = manifest['cases'][str(seed)], RUN/str(seed)
    outcome = dict(seed=seed, observed=False, qualified=False, physical_attempts=0,
                   model_calls=0, training_runs=0, camera_searches=0)
    try:
        with patch.object(nc_session, 'Session', InitialSession):
            with nc_session.opened(case, case['state'], folder=folder, index=1):
                raise AssertionError('Initial preflight must stop at first observation')
    except ObservationComplete:
        outcome.update(observed=True, qualified=True, status='qualified')
    except ObservationRejected:
        outcome.update(observed=True, status='observation_rejected')
    except BaseException:
        outcome.update(status='engineering_failure', traceback=traceback.format_exc())
        raise
    finally:
        save(folder/'outcome.json', outcome)
    assert not read(folder/'bridge.json')['planners']
    assert read(folder/'initial_observation/isolation.json')['passed']
    life = read(folder/'lifecycle.json')
    assert life['released'] and life['actual_close_calls'] == 1 and life['close_error'] is None
    verify()
    print(outcome, flush=True)


if __name__ == '__main__':
    main()
