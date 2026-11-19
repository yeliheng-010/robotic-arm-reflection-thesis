import os
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from audit_motion_live import rebuild, RecordedPlanner, UR5e, set_robot_config, guard_context
from route_geometry import inspect
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_route_bridge_v2'
CASES = (('V0_962501_baseline', 1), ('V0_962501_varied_noisy', 1), ('V0_962501_varied_noisy', 3))


def limits(model, names, desired):
    joints = [model.joint(name).id for name in names]
    assert model.actuator_trnid[:6, 0].tolist() == joints
    rows = []
    for i, jid in enumerate(joints):
        low, high = model.actuator_ctrlrange[i]
        jlow, jhigh = model.jnt_range[jid]
        rows.append(dict(joint=names[i], desired=float(desired[i]), actuator_limited=bool(model.actuator_ctrllimited[i]),
            actuator_range=[float(low), float(high)], actuator_outside=bool(desired[i]<low or desired[i]>high),
            joint_limited=bool(model.jnt_limited[jid]), joint_range=[float(jlow), float(jhigh)],
            joint_outside=bool(desired[i]<jlow or desired[i]>jhigh)))
    return rows


def examine(case, folder):
    step, bridge = read(folder/'step.json'), read(folder/'bridge.json')
    plans = [r for r in bridge['planners'] if r['action']=='move_to_grasp_pose' and r['executed']]
    row = plans[-1]
    observed = [r for r in read(folder/'telemetry.json')['rows'] if r['action']=='close_gripper'][-1]
    robot, env = rebuild(case, row['context'])
    legs = [(r['phase'], RecordedPlanner(r), r['duration']) for r in row['legs']]
    checked = inspect(robot, env, legs, item=case['item'])
    assert checked['feasible']
    desired, actual = robot.get_joint(), np.array(observed['q_rad'])
    desired_tcp, actual_tcp = robot.fkine(desired).t, robot.fkine(actual).t
    stored_tcp = np.array(observed['tcp_fk_xyz_m'])
    target = np.array(bridge['grasp']['actual_target'])
    return dict(condition=case['item']['id'], attempt=step['index'], success=step['success'],
        desired_q=desired.tolist(), actual_q=actual.tolist(), difference_rad=(actual-desired).tolist(),
        periodic_difference_rad=((actual-desired+np.pi)%(2*np.pi)-np.pi).tolist(),
        desired_tcp=desired_tcp.tolist(), actual_tcp=actual_tcp.tolist(), requested_target=target.tolist(),
        desired_target_difference_m=float(np.linalg.norm(desired_tcp-target)),
        actual_target_difference_m=float(np.linalg.norm(actual_tcp-target)),
        recomputed_vs_logged_tcp_m=float(np.linalg.norm(actual_tcp-stored_tcp)),
        gripper_joint_rad=observed['gripper_joint_rad'], bounds=limits(env.mj_model, env.joint_names, desired))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = read(SOURCE/'manifest.json')
    audit = read(SOURCE/'audit_962501.json')
    assert audit['passed'] and audit['manifest_sha256'] == sha(SOURCE/'manifest.json')
    identities, rows = {}, []
    for name, index in CASES:
        folder = SOURCE/'cases'/name/f'attempt_{index}'
        for path in [folder/'step.json', folder/'bridge.json', folder/'telemetry.json']:
            assert sha(path) == audit['identities'][str(path)]
            identities[str(path)] = sha(path)
        case = next(c for c in manifest['cases'] if c['item']['id']==name)
        with patch.object(UR5e, 'set_robot_config', set_robot_config), guard_context(case['item'], {}):
            row = examine(case, folder)
        rows.append(row)
        print(row, flush=True)
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.md', '.sbatch')})
    save(ROOT/'result.json', dict(rows=rows, identities=identities, physical_attempts=0, model_calls=0))


if __name__ == '__main__':
    main()
