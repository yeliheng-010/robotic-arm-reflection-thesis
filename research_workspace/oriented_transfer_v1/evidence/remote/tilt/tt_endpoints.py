from goal_geometry import geometry
from ot_volume import corners
from ot_endpoints import measure
from tt_candidates import candidates

MAX_ENDPOINTS=2048


def inspect(flow, *, item, grasps, poses, record):
    dimensions=geometry(flow,item)
    points=corners(flow.env.mj_model,flow.env.mj_data,item['source'])
    rows=[]
    for candidate in candidates(grasps,poses,points=points,dimensions=dimensions):
        if len(rows)>=MAX_ENDPOINTS:
            return rows,'endpoint_budget_exhausted'
        row=candidate['grasp']
        result=measure(flow,poses[row['pose']],candidate['release'],item=item,config=candidate['config'])
        current=dict(index=len(rows),grasp=row['id'],pose=row['pose'],source_config=row['config'],
            config=candidate['config'],yaw=candidate['yaw'],pitch=candidate['pitch'],
            grid=candidate['grid'],gap=candidate['gap'],**result)
        rows.append(current)
        record(current)
    return rows,'registered_endpoints_exhausted'
