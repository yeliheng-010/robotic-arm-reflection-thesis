"""隔离运动学诊断副本。"""


def clone_robot(robot):
    clone = type(robot)()
    clone._base = robot._base.copy()
    clone.robot.base = clone._base
    clone.set_tool(robot._tool.copy())
    clone.q0 = robot.get_joint().copy()
    for name in ('overhead','inline','wrist'):
        setattr(clone.robot_config,name,getattr(robot.robot_config,name))
    return clone
