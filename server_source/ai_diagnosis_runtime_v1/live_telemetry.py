"""固定仿真步频率记录机器人编码器/命令，不采目标真值或接触事件。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from routecheck.clone import clone_robot
from sensor_math import uniform_rows

STRIDE = 10
ACTIONS = ('move_to_grasp_pose', 'close_gripper', 'move_to_point', 'open_gripper', 'back_to_zero')


class Recorder:
    def __init__(self):
        self.action, self.steps, self.rows, self.robot = 'idle', 0, [], None

    def sample(self, env):
        if self.robot is None:
            self.robot = clone_robot(env.robot)
        q = np.array([float(env.mj_data.joint(name).qpos[0]) for name in env.joint_names])
        return dict(step=self.steps, time_s=float(env.mj_data.time), action=self.action,
                    q_rad=q.tolist(), tcp_fk_xyz_m=self.robot.fkine(q).t.tolist(),
                    command_tcp_xyz_m=env.robot.get_cartesian().t.tolist(),
                    gripper_joint_rad=float(env.mj_data.joint('right_driver_joint').qpos[0]),
                    source='simulated_robot_encoders_and_commands')

    def step_wrapper(self, original):
        def step(env, *args, **kwargs):
            before = float(env.mj_data.time)
            try:
                return original(env, *args, **kwargs)
            finally:
                if float(env.mj_data.time) > before:
                    self.steps += 1
                    if self.steps % STRIDE == 0:
                        self.rows.append(self.sample(env))
        return step

    def action_wrapper(self, original, name):
        def run(flow, *args, **kwargs):
            previous, self.action = self.action, name
            try:
                return original(flow, *args, **kwargs)
            finally:
                self.action = previous
        return run

    def public(self):
        return dict(sampling='fixed_every_10_physics_steps', summary='uniform_time_index_subset',
                    samples=uniform_rows(self.rows), total_samples=len(self.rows))


@contextmanager
def capture():
    import grasp_process as grasp
    from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
    recorder = Recorder()
    with ExitStack() as stack:
        stack.enter_context(patch.object(UR5GraspEnv, 'step', recorder.step_wrapper(UR5GraspEnv.step)))
        for name in ACTIONS:
            original = getattr(grasp.GraspFlow, name)
            stack.enter_context(patch.object(grasp.GraspFlow, name, recorder.action_wrapper(original, name)))
        yield recorder
