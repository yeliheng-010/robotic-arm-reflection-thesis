"""原等式门槛、全关节限位及原禁碰策略。"""
import numpy as np
import mujoco
from qualified_closure_dynamics_v1.initial import equality_check
from guard_runtime import contact_rows
from contact_policy import forbidden
from self_geometry import intersections


def decision(*, equalities, limits, hits, finite, warnings):
    return bool(equalities and all(row['passed'] for row in equalities)
                and all(row['passed'] for row in limits) and not hits and finite and not warnings)


def inspect(model, data, *, source):
    equalities = equality_check(model, data)
    limits = []
    for index in range(model.njnt):
        if not model.jnt_limited[index]:
            continue
        kind = int(model.jnt_type[index])
        if kind not in (int(mujoco.mjtJoint.mjJNT_HINGE), int(mujoco.mjtJoint.mjJNT_SLIDE)):
            raise ValueError('Unsupported limited joint type')
        value = float(data.qpos[model.jnt_qposadr[index]])
        low, high = model.jnt_range[index]
        limits.append(dict(name=model.joint(index).name, value=value, range=[float(low), float(high)],
                           passed=bool(low <= value <= high)))
    contacts = contact_rows(model, data)
    environment = [row for row in contacts if forbidden(row, source)]
    self_hits = intersections(model, data)
    finite = bool(all(np.isfinite(getattr(data, n)).all() for n in ('qpos', 'qvel', 'qacc', 'ctrl', 'efc_pos')))
    warnings = data.warning.number.tolist()
    passed = decision(equalities=equalities, limits=limits, hits=environment+self_hits,
                      finite=finite, warnings=any(warnings))
    return dict(passed=passed, equalities=equalities, limits=limits, all_contacts=contacts,
                forbidden_environment=environment, forbidden_self=self_hits, finite=finite, warnings=warnings)
