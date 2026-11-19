"""只驱动隔离环境，保存漂移、弹簧非对称性和5个参考构型距离。"""
import numpy as np
from qualified_task_v1.integrity import fields
from qualified_closure_dynamics_v1.capture import observe
from qualified_closure_dynamics_v1.protocol import require


def reference_vectors(inputs):
    result = []
    for entry in inputs['configurations']:
        row = entry['saved']
        result.append([value for side in ('right', 'left')
                       for value in [row['angle_rad'], *row['linkage'][side]['joints']]])
    return np.asarray(result)


class Backend:
    def __init__(self, env, gate, *, inputs, source, initial_rejections):
        self.env, self.gate, self.source = env, gate, source
        self.command = np.r_[inputs['command'], 0.0]
        self.references = reference_vectors(inputs)
        self.model_fields = fields(env.mj_model)
        self.initial_rejections = initial_rejections
        self.pending_arrays = None
        self.start_time = float(env.mj_data.time)
        self.fingers = [env.mj_model.joint(f'{s}_{p}_joint').id for s in ('right', 'left')
                        for p in ('driver', 'coupler', 'spring_link', 'follower')]
        self.arms = [env.mj_model.joint(n).id for n in env.joint_names]
        self.initial_tcp = self.tcp()

    def tcp(self):
        data = self.env.mj_data
        body = data.body('2f85_base')
        return body.xpos + body.xmat.reshape(3, 3) @ self.env.robot._tool.t

    def observe(self):
        model, data = self.env.mj_model, self.env.mj_data
        row, arrays = observe(model, data, source=self.source)
        angles = data.qpos[model.jnt_qposadr[self.fingers]]
        arrays.update(finger_angles=angles.copy(),
            finger_velocities=data.qvel[model.jnt_dofadr[self.fingers]].copy(),
            reference_distances=np.max(np.abs(self.references - angles), axis=1),
            spring_asymmetry=np.asarray(angles[2] - angles[6]),
            arm_drift=data.qpos[model.jnt_qposadr[self.arms]] - self.command[:6],
            tcp_drift=self.tcp() - self.initial_tcp)
        row['model_changed'] = fields(model) != self.model_fields
        row['initial_rejections'] = self.initial_rejections if self.gate.task_steps == 0 else []
        row['simulation_time'] = float(data.time)
        row['task_steps'] = self.gate.task_steps
        self.pending_arrays = arrays
        return row

    def step(self, command):
        self.command[-1] = command
        before = self.gate.task_steps
        self.gate.arm(self.env.mj_model, self.env.mj_data)
        self.env.step(self.command)
        require(self.gate.task_steps == before + 1 and not self.gate.pending, 'Native step count')
        elapsed = float(self.env.mj_data.time) - self.start_time
        expected = self.gate.task_steps * float(self.env.mj_model.opt.timestep)
        require(abs(elapsed - expected) <= 1e-9, 'Simulation clock inconsistent')
