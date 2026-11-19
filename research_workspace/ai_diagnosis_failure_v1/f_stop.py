"""预登记工程中止，不伪装为掉落或碰撞；仅在原搬运正常返回后触发。"""
from contextlib import contextmanager
from unittest.mock import patch


class EngineeringStop(RuntimeError):
    pass


class PostObservationProbe(RuntimeError):
    pass


def stop_after(original, trace):
    def run(flow, *args, **kwargs):
        result = original(flow, *args, **kwargs)
        trace.update(triggered=True, checkpoint='after_move_to_point_before_release',
                     time_s=float(flow.env.mj_data.time), natural_failure=False)
        raise EngineeringStop('Pre-registered engineering interruption')
    return run


@contextmanager
def context(trace):
    import grasp_process as grasp
    trace.update(triggered=False, checkpoint='after_move_to_point_before_release', natural_failure=False)
    with patch.object(grasp.GraspFlow, 'move_to_point', stop_after(grasp.GraspFlow.move_to_point, trace)):
        yield
