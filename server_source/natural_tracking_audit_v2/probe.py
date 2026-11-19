"""只重建历史规划几何，检查被环境碰撞过滤器忽略的机器人自接触。"""
import os
from pathlib import Path
from unittest.mock import patch
import mujoco
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from audit_motion_live import rebuild, RecordedPlanner, UR5e, set_robot_config
from cm_geometry import place_robot
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_route_bridge_v2'
CASES = (('V0_962501_baseline', 1), ('V0_962501_varied_noisy', 1), ('V0_962501_varied_noisy', 3))
ROBOTS = ('ur5e_base', '2f85_base')


def contacts(model, data):
    rows = []
    for c in data.contact[:data.ncon]:
        gids = (int(c.geom1), int(c.geom2))
        bids = [int(model.geom_bodyid[g]) for g in gids]
        roots = [model.body(model.body_rootid[b]).name for b in bids]
        if all(r in ROBOTS for r in roots):
            rows.append(dict(geoms=list(gids), bodies=[model.body(b).name for b in bids],
                             roots=roots, distance=float(c.dist)))
    return rows


def examine(case, folder):
    trace = read(folder/'bridge.json')
    groups = [g for g in trace['planners'] if g['action']=='move_to_grasp_pose' and g['executed']]
    results = []
    for group in groups:
        robot, env = rebuild(case, group['context'])
        rows, previous, largest = [], None, 0.
        for leg in group['legs']:
            planner = RecordedPlanner(leg)
            for time in np.linspace(0, leg['duration'], len(leg['samples'])):
                value = planner.interpolate(float(time))
                q = value if isinstance(value, np.ndarray) else robot.ikine(value)
                assert len(q) == 6
                robot.set_joint(q)
                place_robot(robot, env, env.mj_data, q=q)
                if previous is not None:
                    largest = max(largest, float(np.max(np.abs(q-previous))))
                previous = q.copy()
                hits = contacts(env.mj_model, env.mj_data)
                if hits:
                    rows.append(dict(phase=leg['phase'], time=float(time), contacts=hits))
        results.append(dict(samples_with_self_contact=len(rows), first=rows[:2],
                            last=rows[-2:], max_sample_joint_delta_rad=largest))
    observed = [r for r in read(folder/'telemetry.json')['rows'] if r['action']=='close_gripper'][-1]
    place_robot(robot, env, env.mj_data, q=np.array(observed['q_rad']))
    return dict(condition=case['item']['id'], attempt=read(folder/'step.json')['index'], groups=results,
                actual_arm_ideal_flange_self_contacts=contacts(env.mj_model, env.mj_data),
                actuator_gain=env.mj_model.actuator_gainprm[:6].tolist(),
                actuator_bias=env.mj_model.actuator_biasprm[:6].tolist(),
                actuator_force_range=env.mj_model.actuator_forcerange[:6].tolist())


def main():
    assert os.environ.get('SLURM_JOB_ID')
    previous = read(ROOT.parent/'natural_tracking_audit_v1/result.json')
    assert all(sha(p)==h for p,h in previous['identities'].items())
    manifest = read(SOURCE/'manifest.json')
    rows = []
    with patch.object(UR5e, 'set_robot_config', set_robot_config):
        for name, index in CASES:
            case = next(c for c in manifest['cases'] if c['item']['id']==name)
            rows.append(examine(case, SOURCE/'cases'/name/f'attempt_{index}'))
    save(ROOT/'result.json', dict(rows=rows, physical_attempts=0, model_calls=0,
        limitation='Static reconstruction: ideal free gripper flange and initial finger pose; no measured contact forces',
        identities={str(p):sha(p) for p in [Path(__file__), ROOT.parent/'natural_tracking_audit_v1/result.json']}))
    for row in rows:
        print(row, flush=True)


if __name__ == '__main__':
    main()
