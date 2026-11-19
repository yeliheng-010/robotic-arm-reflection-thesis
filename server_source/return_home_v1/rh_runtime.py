"""只替换最终关节归位规划；实际执行仍经过原完整保护。"""
from inspect import signature
from unittest.mock import patch
import numpy as np
import grasp_process as grasp
from reflection.monitors import abort, ErrorType
from cc_runtime import VisibleSession
from cc_common import save
from rh_planner import select, planners


def robot_context(robot, env):
    return dict(qpos=env.mj_data.qpos.tolist(), robot_q=robot.get_joint().tolist(),
        base=robot._base.A.tolist(), tool=robot._tool.A.tolist(), joint_names=list(env.joint_names),
        config=[getattr(robot.robot_config, n) for n in ('overhead', 'inline', 'wrist')])


def wrapper(original, *, item, folder):
    def step(robot, env, *args, **kwargs):
        bound = signature(original).bind(robot, env, *args, **kwargs)
        bound.apply_defaults()
        values = bound.arguments
        np.testing.assert_array_equal(values['q8'], robot.get_joint())
        context = robot_context(robot, env)
        result = select(robot, env, values['q9'], duration=values['time8'], item=item)
        save(folder/'return_plan.json', dict(context=context, goal=list(values['q9']),
            original_duration=values['time8'], result=result))
        option = result['selected']
        if option is None:
            abort(ErrorType.COLLISION, 'No certified return-home route',
                  route_planning_rejected=True, planning_status='return_candidates_exhausted')
        return grasp._run_planners(robot, env, planners(option),
            [0., *option['durations']], values['action'], values['dt'])
    return step


class ReturnSession(VisibleSession):
    def _engine(self):
        replacement = wrapper(grasp.step8_go_home, item=self.case['item'], folder=self.folder)
        with patch.object(grasp, 'step8_go_home', replacement):
            super()._engine()
