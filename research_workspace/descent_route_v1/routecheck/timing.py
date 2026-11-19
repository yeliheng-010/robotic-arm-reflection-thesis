"""保持原位置与时间标定，把目标偏航推迟到下降段。"""
from unittest.mock import patch
import numpy as np
import spatialmath as sm

QUINTIC_COEFFICIENTS = (10,-15,6)


def progress(time,duration):
    u = float(np.clip(time/duration,0,1))
    a,b,c = QUINTIC_COEFFICIENTS
    return a*u**3+b*u**4+c*u**5


class TimedOrientation:
    def __init__(self,planner,rotations,*,duration,rotate):
        self.planner,self.rotations = planner,rotations
        self.duration,self.rotate = duration,rotate

    def interpolate(self,time):
        pose = self.planner.interpolate(time)
        start,goal = self.rotations
        amount = progress(time,self.duration) if self.rotate else 0
        rotation = start.interp(goal,amount)
        return sm.SE3.Trans(*pose.t)*sm.SE3(rotation)

    def __getattr__(self,name):
        return getattr(self.planner,name)


def inject(original,rotations):
    def run(*args,**kwargs):
        assert not kwargs and len(args[2])==3
        values = list(args)
        planners,durations = list(values[2]),values[3]
        planners[1] = TimedOrientation(planners[1],rotations,duration=durations[2],rotate=False)
        planners[2] = TimedOrientation(planners[2],rotations,duration=durations[3],rotate=True)
        values[2] = planners
        return original(*values)
    return run


def routed(original):
    def move(robot,env,**values):
        import grasp_process as grasp
        if values['keep_orientation']:
            return original(robot,env,**values)
        rotations = (sm.SO3(values['T_start'].R),sm.SO3(values['target'].R))
        with patch.object(grasp,'_run_planners',inject(grasp._run_planners,rotations)):
            action,poses = original(robot,env,**values)
        lift,hover,release = poses
        hover = sm.SE3.Trans(*hover.t)*sm.SE3(rotations[0])
        return action,(lift,hover,release)
    return move
