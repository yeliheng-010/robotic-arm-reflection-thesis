"""从已保存预抓取轨迹恢复q0/q1，兼容预抓取分支未改变的情况。"""
from types import SimpleNamespace
import numpy as np
from probe import rebuild, read
from rebuild_v2 import nominal_pose


def joints(bridge, approach):
    first = bridge['planners'][0]
    assert len(first['legs']) == 1 and first['executed']
    samples = np.array(first['legs'][0]['samples'])
    assert samples.shape == (51, 6)
    q0, q1 = samples[0].copy(), samples[-1].copy()
    np.testing.assert_allclose(first['context']['robot_q'], q0, atol=1e-9, rtol=0)
    if 'q1' in approach:
        np.testing.assert_allclose(approach['q1'], q1, atol=1e-9, rtol=0)
    return q0, q1


def flow_for(case, step, bridge):
    robot, env = rebuild(case, bridge['planners'][0]['context'])
    record = read(step['result_path'])['records'][0]
    q0, q1 = joints(bridge, record['approach_plan'])
    return SimpleNamespace(robot=robot, env=env, q0=q0, q1=q1, T_wo=nominal_pose(bridge))
