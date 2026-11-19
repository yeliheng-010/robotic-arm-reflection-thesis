"""进程内限定接触例外与释放门控，冻结引擎和错误枚举不变。"""
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import reflection.monitors as monitors
import stability.prepose as prepose
import cm_geometry
from reflection.sim_sensing import grasped_objects
from guard_policy import forbidden, release_reason, ROBOTS, XY_TOLERANCE_M, Z_TOLERANCE_M


def contact_rows(model, data):
    rows = []
    for contact in data.contact[:data.ncon]:
        gids = (contact.geom1, contact.geom2)
        roots = [model.body(model.body_rootid[model.geom_bodyid[g]]).name for g in gids]
        rows.append(dict(roots=roots, geoms=[model.geom(g).name for g in gids],
                         distance=float(contact.dist), point=contact.pos.tolist()))
    return rows


def contact_checker(source):
    def check(model, data, *, ignore=()):
        rows = [row for row in contact_rows(model, data) if forbidden(row, source)]
        return [tuple(row['roots']) if row['roots'][0] in ROBOTS else tuple(reversed(row['roots']))
                for row in rows]
    return check


def release_evidence(flow, source):
    data = flow.env.mj_data
    flange = np.eye(4)
    flange[:3, :3] = data.body('2f85_base').xmat.reshape(3, 3)
    flange[:3, 3] = data.body('2f85_base').xpos
    actual = (flange @ flow.robot._tool.A)[:3, 3]
    expected = flow.T6.t
    held = source in grasped_objects(flow.env.mj_model, data)
    return dict(held=held, actual=actual.tolist(), expected=expected.tolist(),
                xy_error_m=float(np.linalg.norm(actual[:2]-expected[:2])),
                z_error_m=float(abs(actual[2]-expected[2])),
                xy_tolerance_m=XY_TOLERANCE_M, z_tolerance_m=Z_TOLERANCE_M,
                time=float(data.time), signal_source='simulation_pose_and_pad_contacts')


def guarded_open(original, item, trace):
    def run(flow, *args, **kwargs):
        evidence = release_evidence(flow, item['source'])
        reason = release_reason(evidence)
        trace.update(release_checked=True, release=evidence, reason=reason, open_called=False)
        if reason:
            monitors.abort(monitors.ErrorType(reason), 'Release precondition not satisfied',
                           guard_kind='release_precondition', release_guard=evidence)
        trace['open_called'] = True
        return original(flow, *args, **kwargs)
    return run


@contextmanager
def context(item, trace, *, contacts=True):
    trace.update(release_checked=False, open_called=False, strict_contacts=contacts)
    with ExitStack() as stack:
        if contacts:
            checker = contact_checker(item['source'])
            for module in (monitors, prepose, cm_geometry):
                stack.enter_context(patch.object(module, 'robot_environment_contacts', checker))
        stack.enter_context(patch.object(grasp.GraspFlow, 'open_gripper',
                            guarded_open(grasp.GraspFlow.open_gripper, item, trace)))
        yield
