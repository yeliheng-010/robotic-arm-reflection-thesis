"""私有刚性持物预测状态的观察门禁；不作为真实持物数据。"""
import spatialmath as sm
import numpy as np
from qualified_task_v1.snapshot import clone
from qualified_task_v1.observer import observe, ObservationRejected
from cm_geometry import place_robot
from ot_volume import body_pose
from ot_volume_v2 import place


def inspect(flow, case, *, plan, folder):
    row = plan['selected']
    snapshot = clone(flow.env)
    snapshot.joint_names = list(flow.env.joint_names)
    grasp = sm.SE3(np.asarray(row['pose']))
    lifted = sm.SE3.Trans(0., 0., row['lift'])*grasp
    from routecheck.clone import clone_robot
    robot = clone_robot(flow.robot)
    robot.set_joint(np.asarray(row['q1']))
    q = robot.ikine(lifted)
    assert len(q) == 6
    initial = body_pose(snapshot.mj_model, snapshot.mj_data, case['item']['source'])
    place_robot(robot, snapshot, snapshot.mj_data, q=q)
    place(snapshot.mj_model, snapshot.mj_data, source=case['item']['source'],
        initial=initial, grasp=grasp, release=lifted)
    try:
        observe(snapshot, case['config'], folder=folder)
        accepted = True
    except ObservationRejected:
        accepted = False
    return dict(accepted=accepted, predicted_rigid_held_state=True, actual_held_verified=False,
        private_safety_evaluation_only=True, model_calls=0, physical_attempts=0)
