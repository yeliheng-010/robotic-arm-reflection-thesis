"""从冻结XML构造隔离夹爪运动学模型；不含接触或场景。"""
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
from qualified_closure_dynamics_v1.protocol import require

STATE_QPOS_OFFSET = 1
FULL_FREE_QPOS = 6


def isolated_xml(source):
    root = ET.parse(source).getroot()
    for node in list(root):
        if node.tag in ('asset', 'contact', 'actuator', 'tendon', 'keyframe', 'compiler'):
            root.remove(node)
    for parent in root.iter():
        for node in list(parent):
            if node.tag in ('geom', 'site', 'mesh'):
                parent.remove(node)
    root.insert(0, ET.Element('compiler', dict(angle='radian', autolimits='true')))
    base = root.find("./worldbody/body[@name='2f85_base']")
    require(base is not None and base.find('inertial') is None, 'Unexpected root inertia')
    ET.SubElement(base, 'inertial', dict(pos='0 0 0', mass='1', diaginertia='1 1 1'))
    return ET.tostring(root, encoding='unicode')


def verify_model(model, parameters):
    require(model.nq == 15 and model.nv == 14 and model.neq == 3, 'Unexpected isolated dimensions')
    require(model.ngeom == 0 and model.nu == 0, 'Isolated model has geometry or actuation')
    for row in parameters['joints']:
        joint = model.joint(row['name'])
        np.testing.assert_array_equal(row['range'], model.jnt_range[joint.id])
        require(int(model.jnt_type[joint.id]) == int(mujoco.mjtJoint.mjJNT_HINGE), 'Unexpected joint type')
    for row in parameters['equalities']:
        index = row['id']
        require(int(model.eq_type[index]) == row['type'], 'Equality type changed')
        np.testing.assert_allclose(row['data'], model.eq_data[index], atol=1e-15, rtol=0)
        accessor = model.body if row['type'] == 0 else model.joint
        require([accessor(int(i)).name for i in (model.eq_obj1id[index], model.eq_obj2id[index])]
                == row['names'], 'Equality bodies changed')


def check_state_layout(model):
    data = mujoco.MjData(model)
    data.time = 2.25
    data.qpos[:] = np.arange(model.nq, dtype=float) / 10
    values = np.empty(mujoco.mj_stateSize(model, mujoco.mjtState.mjSTATE_INTEGRATION))
    mujoco.mj_getState(model, data, values, mujoco.mjtState.mjSTATE_INTEGRATION)
    require(values[0] == data.time, 'State time prefix changed')
    np.testing.assert_array_equal(data.qpos, values[STATE_QPOS_OFFSET:STATE_QPOS_OFFSET + model.nq])
    return dict(time_offset=0, qpos_offset=STATE_QPOS_OFFSET, api_layout_verified=True)


def qpos_from_state(state, parameters):
    result = {'2f85': state[STATE_QPOS_OFFSET + FULL_FREE_QPOS:STATE_QPOS_OFFSET + FULL_FREE_QPOS + 7]}
    for row in parameters['joints']:
        require(row['qpos_address'] == row['id'] + 6, 'Frozen full-model joint layout changed')
        result[row['name']] = float(state[STATE_QPOS_OFFSET + row['qpos_address']])
    return result


def evaluate(model, state, parameters):
    data = mujoco.MjData(model)
    for name, value in qpos_from_state(state, parameters).items():
        data.joint(name).qpos[:] = value
    mujoco.mj_kinematics(model, data)
    frame = data.body('2f85_base').xmat.reshape(3, 3)
    rows = []
    for index in range(2):
        left, right = model.body(int(model.eq_obj1id[index])), model.body(int(model.eq_obj2id[index]))
        a = data.xpos[left.id] + data.xmat[left.id].reshape(3, 3) @ model.eq_data[index, :3]
        b = data.xpos[right.id] + data.xmat[right.id].reshape(3, 3) @ model.eq_data[index, 3:6]
        residual = a - b
        rows.append(dict(id=index, world=residual.tolist(), local=(frame.T @ residual).tolist(),
            maximum_abs=float(np.max(np.abs(residual))), norm=float(np.linalg.norm(residual)),
            passed=bool(np.max(np.abs(residual)) <= 1e-7)))
    return rows
