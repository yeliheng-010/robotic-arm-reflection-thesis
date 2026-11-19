"""共享执行器：显式参数/配置映射，保留真实目标姿态。"""
from contextlib import contextmanager
from unittest.mock import patch
from reflection.reflector import Parameters
from semanticfix2.engine import SemanticEngine
from routecheck.adapter import options,plans
from routecheck.timing import routed
from routecheck.static import state as snapshot,unchanged
from loopstudy.actions import PROFILES,validate


def observe(original,state,trace):
    def move(robot,env,**values):
        before = snapshot(robot,env)
        applied = options(values,PROFILES[state['profile']])
        planned = plans(original,(robot,env),applied)
        trace.update(profile=state['profile'],yaw_deg=PROFILES[state['profile']],
            start=values['T_start'].A.tolist(),target_xyz=list(values['target']),
            planned_poses=[p.A.tolist() for p in planned['poses']],
            keep_orientation=applied['keep_orientation'],durations=planned['durations'],
            lift_height=values['lift_height'],dt=values['dt'])
        unchanged(before,snapshot(robot,env))
        trace['observation_state_unchanged']=True
        return original(robot,env,**applied)
    return move


@contextmanager
def capture(state,trace):
    import grasp_process as grasp
    with patch.object(grasp,'move_to_point',observe(routed(grasp.move_to_point),state,trace)):
        yield


def engine_class(state):
    state = validate(state)
    class LoopEngine(SemanticEngine):
        def _attempt(self,*args,**kwargs):
            values,trace = list(args),{}
            values[5] = Parameters().updated(state['parameters'])
            with capture(state,trace):
                record,report = super()._attempt(*values,**kwargs)
            record['execution_adapter']=trace
            record['executor_state']=state
            return record,report
    return LoopEngine
