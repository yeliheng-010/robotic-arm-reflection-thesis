"""保存末态的接触复核与静态反事实；不重跑闭合或生成控制命令。"""
import numpy as np
import mujoco
from qualified_execution_v1.environment import opened, state
from qualified_execution_v1.common import ROOT, PROJECT, RUN, SEED, read, save, sha, verify, case
from guard_runtime import contact_rows
from contact_policy import forbidden
from cm_geometry import place_robot
from routecheck.clone import clone_robot
from reflection import monitors


def restored(model, values):
    data = mujoco.MjData(model)
    mujoco.mj_setState(model, data, values, mujoco.mjtState.mjSTATE_INTEGRATION)
    mujoco.mj_forward(model, data)
    return data


def finger_copy(model, data, reference):
    root = model.body('2f85_base').id
    ids = [i for i in range(model.njnt) if model.body_rootid[model.jnt_bodyid[i]] == root
        and model.jnt_type[i] in (mujoco.mjtJoint.mjJNT_HINGE, mujoco.mjtJoint.mjJNT_SLIDE)]
    for index in ids:
        adr = model.jnt_qposadr[index]
        data.qpos[adr] = reference.qpos[adr]
    mujoco.mj_forward(model, data)
    return [model.joint(i).name for i in ids]


def contacts(model, data, item):
    return [row for row in contact_rows(model, data) if forbidden(row, item['source'])]


def compare(env, item, *, initial, final, command):
    model = env.mj_model
    original, end = restored(model, initial), restored(model, final)
    actual = contacts(model, end, item)
    expected = read(RUN/'physical/result.json')['safety_error']['evidence']['contacts']
    hits = monitors.robot_environment_contacts(model, end, ignore=(item['source'], item['destination']))
    assert sorted(map(tuple, hits)) == sorted(map(tuple, expected))
    robot = clone_robot(env.robot)
    commanded = restored(model, final)
    place_robot(robot, env, commanded, q=command)
    reopened = restored(model, final)
    names = finger_copy(model, reopened, original)
    synthetic = restored(model, initial)
    finger_copy(model, synthetic, end)
    place_robot(robot, env, synthetic, q=command)
    flange = np.eye(4)
    flange[:3, :3], flange[:3, 3] = end.body('2f85_base').xmat.reshape(3, 3), end.body('2f85_base').xpos
    actual_tcp, expected_tcp = flange@robot._tool.A, robot.fkine(command).A
    return dict(actual_contacts=actual, live_rejection_reproduced=True,
        final_scene_commanded_arm=contacts(model, commanded, item),
        final_scene_initial_fingers=contacts(model, reopened, item),
        initial_scene_commanded_arm_final_fingers=contacts(model, synthetic, item),
        replaced_joints=names, tcp_position_error_m=float(np.linalg.norm(actual_tcp[:3, 3]-expected_tcp[:3, 3])),
        tcp_rotation_matrix_max_error=float(np.max(np.abs(actual_tcp[:3, :3]-expected_tcp[:3, :3]))),
        right_driver_angle_rad=float(end.joint('right_driver_joint').qpos[0]),
        counterfactuals_are_static=True, causal_proof=False, physical_attempts=0, model_calls=0)


def main():
    verify()
    folder = RUN/'physical'
    frozen = {str(p): sha(p) for p in folder.rglob('*') if p.is_file()}
    save(RUN/'contact_audit_manifest.json', dict(identities=frozen, source_sha256=sha(ROOT/'contact_audit.py')))
    with np.load(folder/'final_state.npz') as data:
        final, command = data['state'], data['robot_q']
    source = PROJECT/f'qualified_task_v1/run/initial_v2/{SEED}/initial_observation/source_state.npz'
    with np.load(source) as data:
        initial = data['state']
    item = case()
    with opened(item, {}, static=True) as env:
        before = state(env)
        result = compare(env, item['item'], initial=initial, final=final, command=command)
        np.testing.assert_array_equal(before, state(env))
    assert all(sha(p) == h for p, h in frozen.items())
    save(RUN/'contact_audit.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
