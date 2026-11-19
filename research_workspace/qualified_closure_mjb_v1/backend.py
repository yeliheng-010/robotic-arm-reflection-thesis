"""直接驱动MJB数据；双时点采集继续使用原禁碰策略。"""
import numpy as np
import mujoco
from qualified_closure_mjb_v1.protocol import proposal, require
from qualified_closure_dynamics_v1.capture import observe
from qualified_closure_dynamics_v1.backend import reference_vectors
from qualified_task_v1.integrity import fields


class Backend:
    def __init__(self, model, data, *, gate, inputs, initial_rejections):
        self.model, self.data, self.gate = model, data, gate
        self.plan, self.inputs = proposal(), inputs
        self.command = np.r_[inputs['command'], 0.0]
        self.references, self.model_fields = reference_vectors(inputs), fields(model)
        self.initial_rejections, self.pending_arrays = initial_rejections, None
        self.start_time = float(data.time)
        self.fingers = [model.joint(f'{s}_{p}_joint').id for s in ('right', 'left')
                        for p in ('driver', 'coupler', 'spring_link', 'follower')]
        self.arms = list(range(6))
        self.initial_tcp = self.tcp()

    def tcp(self):
        body = self.data.body('2f85_base')
        return body.xpos + body.xmat.reshape(3, 3) @ np.asarray(self.plan['tcp_local_translation_m'])

    def observe(self):
        model, data = self.model, self.data
        elapsed = float(data.time)-self.start_time
        require(abs(elapsed-self.gate.returns*model.opt.timestep) <= 1e-9, 'Simulation clock mismatch')
        require(self.gate.requests == self.gate.returns and not self.gate.pending, 'Incomplete native step')
        row, arrays = observe(model, data, source=self.plan['source'])
        angles = data.qpos[model.jnt_qposadr[self.fingers]]
        arrays.update(finger_angles=angles.copy(), finger_velocities=data.qvel[model.jnt_dofadr[self.fingers]].copy(),
            reference_distances=np.max(np.abs(self.references-angles), axis=1),
            spring_asymmetry=np.asarray(angles[2]-angles[6]),
            arm_drift=data.qpos[model.jnt_qposadr[self.arms]]-self.command[:6],
            tcp_drift=self.tcp()-self.initial_tcp)
        row.update(model_changed=fields(model) != self.model_fields,
                   initial_rejections=self.initial_rejections if self.gate.returns == 0 else [],
                   simulation_time=float(data.time), task_steps=self.gate.returns)
        self.pending_arrays = arrays
        return row

    def step(self, command):
        self.command[-1] = command
        self.gate.arm(self.model, self.data)
        self.data.ctrl[:] = self.command
        mujoco.mj_step(self.model, self.data)
