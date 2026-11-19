"""沿用环境接触定义，覆盖接近、夹持、释放和回程阶段。"""
from contextlib import contextmanager
from unittest.mock import patch
import reflection.monitors as original


def contact_details(env):
    if env.mj_model is None:
        return []
    model, data = env.mj_model, env.mj_data
    return [{'geoms': [model.geom(c.geom1).name, model.geom(c.geom2).name],
             'bodies': [model.body(model.geom_bodyid[g]).name for g in (c.geom1, c.geom2)],
             'distance': float(c.dist), 'position': c.pos.tolist()}
            for c in data.contact[:data.ncon]]


def check_environment(monitor):
    hits = original.robot_environment_contacts(monitor.env.mj_model, monitor.env.mj_data,
        ignore=(monitor.source, monitor.destination))
    if hits:
        original.abort(original.ErrorType.COLLISION, 'Unexpected robot-environment contact',
            contacts=hits, phase=monitor.phase, signal_source='simulation_contacts',
            contact_geometry=contact_details(monitor.env))


@contextmanager
def guard_environment():
    from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
    tick, check = original.ExecutionMonitor.tick, original.ExecutionMonitor.check_grasp
    init, step = original.ExecutionMonitor.__init__, UR5GraspEnv.step
    monitors = {}

    def guarded_init(monitor, *args, **kwargs):
        init(monitor, *args, **kwargs)
        monitors[monitor.env] = monitor

    def guarded_step(env, action=None):
        result = step(env, action)
        monitor = monitors.get(env)
        if monitor is not None and monitor.phase != 'carry':
            monitor.tick()
        return result

    def guarded_tick(monitor):
        check_environment(monitor)
        return tick(monitor)

    def guarded_grasp(monitor, residual):
        check_environment(monitor)
        return check(monitor, residual)

    with patch.object(original.ExecutionMonitor, '__init__', guarded_init), patch.object(
            UR5GraspEnv, 'step', guarded_step), patch.object(
            original.ExecutionMonitor, 'tick', guarded_tick), patch.object(
            original.ExecutionMonitor, 'check_grasp', guarded_grasp):
        yield
