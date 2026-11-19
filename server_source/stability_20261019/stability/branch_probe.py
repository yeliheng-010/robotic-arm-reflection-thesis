"""验证静态可行的肩肘分支是否能完成动态接近；仅诊断。"""
import json
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import os
from contextlib import ExitStack
from unittest.mock import patch
import spatialmath as sm
from stability.experiment import OUT


def execute(wrist):
    from reflection.__main__ import bootstrap
    bootstrap()
    import grasp_process as grasp
    from stability.runtime import StableEngine
    from manipulator_grasp.arm.robot import UR5e
    from stability.kinematics import set_robot_config
    original = grasp.GraspFlow.move_to_grasp_pose
    selected = {}

    def elevated(flow, *args, **kwargs):
        robot, saved = flow.robot, flow.robot.get_joint().copy()
        robot.set_joint(flow.q1)
        for name, value in zip(('overhead', 'inline', 'wrist'), (-1, -1, wrist)):
            setattr(robot.robot_config, name, value)
        pose = sm.SE3.Trans(0, 0, .35) * flow.T_wo * sm.SE3(-.1, 0, 0)
        q = robot.ikine(pose)
        robot.set_joint(saved)
        if len(q) != 6:
            raise AssertionError('Elevated prepose not reachable')
        flow.q1 = q
        selected['q1'] = q.tolist()
        return original(flow, *args, **kwargs)

    engine = StableEngine(max_attempts=1, headless=True, task_parser='rule', scene_jitter=.012)
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(grasp.GraspFlow, 'move_to_grasp_pose', elevated))
            if os.environ.get('CORRECTED_IK'):
                stack.enter_context(patch.object(UR5e, 'set_robot_config', set_robot_config))
            result = engine.run(source='OrangeSphere', destination='BlueBin', fault='collision',
                seed=2000, method='baseline', output=OUT/run_name()/str(wrist))
        r = result['records'][0]
        return dict(wrist=wrist, success=result['success'], error=r['error'],
                    diagnostics=r['diagnostics'], selected=selected)
    finally:
        engine.close()


def run_name():
    return 'branch_probe_corrected' if os.environ.get('CORRECTED_IK') else 'branch_probe'


def main():
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn')) as pool:
        rows = list(pool.map(execute, (-1, 1)))
    (OUT/(run_name()+'.json')).write_text(json.dumps(rows, indent=2))
    print(json.dumps([dict(wrist=r['wrist'], success=r['success'], error=(r['error'] or {}).get('error_type')) for r in rows]))


if __name__ == '__main__':
    main()

