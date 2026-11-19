"""接近阶段提前拒绝时，最后规划点是T2，不是尚未规划的T3。"""
from types import SimpleNamespace
import numpy as np
import spatialmath as sm
from probe import rebuild, read

APPROACH_OFFSET_M = (-.1, 0., 0.)


def nominal_pose(bridge):
    assert len(bridge['planners']) == 2, 'This revision only supports rejection during approach'
    last = bridge['planners'][-1]
    assert not last['executed'] and len(last['legs']) == 1
    approach = sm.SE3(np.array(last['legs'][0]['samples'][-1]))
    nominal = approach * sm.SE3(*[-v for v in APPROACH_OFFSET_M])
    np.testing.assert_allclose(bridge['grasp']['actual_target'], nominal.t, atol=1e-8, rtol=0)
    return nominal


def flow_for(case, step, bridge):
    robot, env = rebuild(case, bridge['planners'][0]['context'])
    record = read(step['result_path'])['records'][0]
    return SimpleNamespace(robot=robot, env=env, q0=robot.get_joint().copy(),
        q1=np.array(record['approach_plan']['q1']), T_wo=nominal_pose(bridge))
