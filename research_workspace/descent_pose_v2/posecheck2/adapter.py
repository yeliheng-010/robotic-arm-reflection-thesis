"""使用已有SE3接口调整放置偏航，不修改公共参数或原执行器。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import spatialmath as sm

YAW_DEGREES = (0,-45,45,-90,90)


def options(values,yaw):
    if yaw not in YAW_DEGREES:
        raise ValueError('Unregistered yaw')
    result = dict(values)
    if yaw:
        rotation = sm.SO3.Rz(yaw,unit='deg')*sm.SO3(values['T_start'].R)
        result['target'] = sm.SE3.Trans(*values['target'])*sm.SE3(rotation)
        result['keep_orientation'] = False
    return result


def plans(original,context,values):
    import grasp_process as grasp
    captured = {}
    def collect(robot,env,planners,*,durations,action):
        captured.update(planners=planners,durations=durations)
        return action
    def intercept(*args,**kwargs):
        assert not kwargs
        return collect(args[0],args[1],args[2],durations=args[3],action=args[4])
    with patch.object(grasp,'_run_planners',intercept):
        _,poses = original(context[0],context[1],**values)
    captured['poses'] = poses
    return captured


def observe(original,yaw,trace):
    def move(robot,env,**values):
        from posecheck2.static import inspect,state,unchanged
        before = state(robot,env)
        applied = options(values,yaw)
        planned = plans(original,(robot,env),applied)
        trace.update(yaw_deg=yaw,source='fixed_executor_pose_diagnostic',
                     start=values['T_start'].A.tolist(),target_xyz=list(values['target']),
                     keep_orientation=applied['keep_orientation'],
                     planned_poses=[p.A.tolist() for p in planned['poses']],
                     lift_height=values['lift_height'],dt=values['dt'],
                     durations=planned['durations'],joint_config=before['config'])
        if yaw==0:
            trace['static'] = [inspect(robot,env,plans(original,(robot,env),options(values,a)),yaw=a)
                               for a in YAW_DEGREES]
        unchanged(before,state(robot,env))
        trace['observation_state_unchanged'] = True
        trace['execution_entered'] = True
        return original(robot,env,**applied)
    return move


@contextmanager
def capture(yaw,trace):
    import grasp_process as grasp
    with patch.object(grasp,'move_to_point',observe(grasp.move_to_point,yaw,trace)):
        yield
