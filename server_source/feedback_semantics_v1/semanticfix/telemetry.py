"""在原监视器抛出碰撞后读取同一帧数据，不改变阈值或执行。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np


def geom_detail(model,data,gid):
    gid = int(gid)
    bid = int(model.geom_bodyid[gid])
    root = int(model.body_rootid[bid])
    box = np.asarray(model.geom_aabb[gid])
    rotation = data.geom_xmat[gid].reshape(3,3)
    center = data.geom_xpos[gid]+rotation@box[:3]
    extent = np.abs(rotation)@box[3:]
    return dict(geom_id=gid,geom=model.geom(gid).name or f'geom#{gid}',
                body_id=bid,body=model.body(bid).name,root_id=root,root=model.body(root).name,
                geom_type=int(model.geom_type[gid]),
                aabb=dict(low=(center-extent).tolist(),high=(center+extent).tolist(),
                          source='compiled_geom_local_aabb_transformed_to_world'),
                native=dict(local_aabb=box.tolist(),xpos=data.geom_xpos[gid].tolist(),
                            xmat=data.geom_xmat[gid].tolist()))


def contact_details(model,data,pairs):
    wanted = {frozenset(pair) for pair in pairs}
    rows = []
    for contact in data.contact[:data.ncon]:
        gids = (int(contact.geom1),int(contact.geom2))
        roots = [model.body(int(model.body_rootid[model.geom_bodyid[g]])).name for g in gids]
        if frozenset(roots) not in wanted:
            continue
        rows.append(dict(geometries=[geom_detail(model,data,g) for g in gids],
                         point=contact.pos.tolist(),distance=float(contact.dist)))
    return dict(schema='actual-contact-v1',source='simulation_contact_geometry',
                simulation_time=float(data.time),contacts=rows)


@contextmanager
def capture():
    from reflection.monitors import ExecutionMonitor
    from reflection.errors import TaskAbort
    original = ExecutionMonitor.tick

    def tick(monitor):
        try:
            return original(monitor)
        except TaskAbort as error:
            report = error.report
            if report.to_dict()['error_type']=='collision':
                report.evidence['contact_details'] = contact_details(
                    monitor.env.mj_model,monitor.env.mj_data,report.evidence.get('contacts',[]))
            raise

    with patch.object(ExecutionMonitor,'tick',tick):
        yield
