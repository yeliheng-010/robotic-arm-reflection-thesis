import json
import sys
from collections import Counter
from pathlib import Path
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from goal_endpoints import inspect, CONFIGS
from ot_inputs import opened
from top_fit import estimate
from span import span
from geometry.candidates import MAX_WIDTH, WIDTH_MARGIN
from routecheck.static import state, unchanged
from proposals import grasps
from common import ROOT, read, save, sha, verify


def evaluate(flow, entry, points):
    rows = []
    for candidate in grasps(flow.T_wo,estimate(points)):
        pose = candidate['pose']
        width = span(points,pose.R[:,1])+WIDTH_MARGIN
        metadata = dict(id=candidate['id'],pose=pose.A.tolist(),required_width_m=width)
        if width > MAX_WIDTH:
            rows.append(dict(metadata,ok=False,reason='observed_span',config=None))
            continue
        for config in CONFIGS:
            result = inspect(flow,pose,config=config,item=entry['case']['item'])
            rows.append(dict(metadata,config=list(config),**result))
    return rows


def main(mode):
    entry = verify(ROOT/'manifest.json')['entry']
    folder = ROOT/mode/'grasp_964347'
    folder.mkdir(parents=True,exist_ok=False)
    with np.load(Path(entry['folder'])/'span_inputs.npz') as data:
        points = data['world_points']
    with opened(entry) as (flow, _, old_poses):
        before = state(flow.robot,flow.env)
        rows = evaluate(flow,entry,points)
        unchanged(before,state(flow.robot,flow.env))
    with (folder/'endpoints.jsonl').open('x') as stream:
        for row in rows:
            stream.write(json.dumps(row,allow_nan=False)+'\n')
    if mode=='audit':
        assert sha(folder/'endpoints.jsonl')==sha(ROOT/'probe/grasp_964347/endpoints.jsonl')
    result = dict(passed=True,safe_endpoints=sum(r['ok'] for r in rows),checks=len(rows),
        reasons=dict(Counter(r.get('reason') or 'ok' for r in rows)),unchanged=True,
        independent=mode=='audit',full_path_verified=False,physical_attempts=0)
    save(folder/'result.json',dict(result,identities={str(folder/'endpoints.jsonl'):sha(folder/'endpoints.jsonl')}))
    print(result,flush=True)


if __name__=='__main__':
    main(sys.argv[1])
