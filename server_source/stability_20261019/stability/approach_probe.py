"""只观测抓取前实际TCP和环境接触，定位空抓而不改变监测器。"""
import json
from unittest.mock import patch
from reflection.monitors import ExecutionMonitor
from reflection.sim_sensing import robot_environment_contacts
from stability.runtime import StableEngine
from stability.experiment import OUT


def run(condition):
    state = {'idle_contact_frames': 0, 'first_contacts': None}
    original_tick = ExecutionMonitor.tick
    original_check = ExecutionMonitor.check_grasp

    def tick(monitor):
        if monitor.phase == 'idle':
            contacts = robot_environment_contacts(monitor.env.mj_model, monitor.env.mj_data,
                                                 ignore=(monitor.source, monitor.destination))
            if contacts:
                state['idle_contact_frames'] += 1
                if state['first_contacts'] is None:
                    state['first_contacts'] = contacts
        return original_tick(monitor)

    def check(monitor, residual):
        state['actual_tcp_xyz'] = monitor.env.robot.get_cartesian().t.tolist()
        state['target_xyz'] = monitor.env.mj_data.body(monitor.source).xpos.tolist()
        state['contacts_at_grasp'] = robot_environment_contacts(
            monitor.env.mj_model, monitor.env.mj_data, ignore=(monitor.source, monitor.destination))
        return original_check(monitor, residual)

    engine = StableEngine(max_attempts=1, headless=True, task_parser='rule', scene_jitter=.012)
    try:
        with patch.object(ExecutionMonitor, 'tick', tick), patch.object(ExecutionMonitor, 'check_grasp', check):
            result = engine.run(source='OrangeSphere', destination='BlueBin', fault=condition,
                seed=2000, method='baseline', output=OUT/'approach_probe'/condition)
        state['first'] = {k: result['records'][0][k] for k in ('error', 'diagnostics', 'accepted')}
        return state
    finally:
        engine.close()


def main():
    result = {condition: run(condition) for condition in ('none', 'collision')}
    (OUT/'approach-probe.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

