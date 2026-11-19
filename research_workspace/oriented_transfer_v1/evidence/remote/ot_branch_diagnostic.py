"""固定首抓点/中心最低高度的8朝向×8IK分支只读诊断。"""
import json
from itertools import product
from pathlib import Path
from collections import Counter
import numpy as np
import mujoco
from reflection.__main__ import bootstrap
bootstrap()
from ot_inputs import opened
from ot_register_v2 import ROOT,RUN,save,sha,verify
from ot_endpoints import candidates,measure,YAWS
from ot_volume import corners,body_pose
from ot_volume_v2 import context,place
from goal_geometry import geometry
from cm_geometry import place_robot
from routecheck.clone import clone_robot
from routecheck.static import state,unchanged

CONFIGS=tuple(product((1,-1),repeat=3))


def details(flow, result, *, item, grasp, release):
    if 'q' not in result:
        return []
    model=flow.env.mj_model
    data=mujoco.MjData(model)
    data.qpos[:]=flow.env.mj_data.qpos
    initial=body_pose(model,flow.env.mj_data,item['source'])
    place(model,data,source=item['source'],initial=initial,grasp=grasp,release=release)
    place_robot(clone_robot(flow.robot),flow.env,data,q=np.array(result['q']))
    rows=[]
    for contact in data.contact[:data.ncon]:
        gids=[int(contact.geom1),int(contact.geom2)]
        bids=[int(model.geom_bodyid[g]) for g in gids]
        roots=[model.body(model.body_rootid[b]).name for b in bids]
        if 'ur5e_base' not in roots or item['destination'] not in roots or contact.dist>=0:
            continue
        rows.append(dict(bodies=[model.body(b).name for b in bids],distance=float(contact.dist)))
    return rows


def main():
    entry=verify(RUN/'manifest.json')['rows'][0]
    rows=[]
    with opened(entry) as (flow,grasps,poses),context():
        before=state(flow.robot,flow.env)
        points=corners(flow.env.mj_model,flow.env.mj_data,entry['case']['item']['source'])
        sequence=candidates(grasps[:1],poses,points=points,dimensions=geometry(flow,entry['case']['item']))
        for candidate in sequence:
            if candidate['grid']!=[0,0] or candidate['gap']!=.01:
                break
            grasp=poses[candidate['grasp']['pose']]
            for config in CONFIGS:
                result=measure(flow,grasp,candidate['release'],item=entry['case']['item'],config=config)
                contacts=details(flow,result,item=entry['case']['item'],grasp=grasp,release=candidate['release'])
                rows.append(dict(yaw=candidate['yaw'],config=list(config),
                    original_config=candidate['grasp']['config'],private_contacts=contacts,**result))
        unchanged(before,state(flow.robot,flow.env))
    save(ROOT/'branch_diagnostic.json',dict(rows=rows,passed=True,physical_attempts=0,model_calls=0,
        identities={str(RUN/'manifest.json'):sha(RUN/'manifest.json'),str(Path(__file__)):sha(__file__)}))
    print(dict(checks=len(rows),passing=sum(r['ok'] for r in rows),
        reasons=dict(Counter(r.get('reason') or 'ok' for r in rows)),
        body_pairs=dict(Counter('|'.join(c['bodies']) for r in rows for c in r['private_contacts']))),flush=True)


if __name__=='__main__':
    main()
