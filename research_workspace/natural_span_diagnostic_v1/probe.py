import os
import json
from pathlib import Path
from itertools import product
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from route_audit_v3 import rebuild
from cm_pose import poses
from span import span
from f_common import read, save, sha
import spatialmath as sm

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'natural_span_pilot_v1'
NAME = 'P0_963008_varied_noisy'


def geometry(case, plan):
    flow = rebuild(case, plan)
    model, data = flow.env.mj_model, flow.env.mj_data
    geom = model.geom('red_block').id
    half = model.geom_size[geom]
    rotation = data.geom_xmat[geom].reshape(3, 3)
    center = data.geom_xpos[geom]
    vertices = np.array(list(product((-1., 1.), repeat=3)))*half
    return vertices@rotation.T+center, center


def closing(folder):
    rows = [json.loads(s) for s in (folder/'contacts.jsonl').read_text().splitlines()]
    end = [r for r in rows if r['action'] == 'close_gripper' and r['event'] == 'end_or_abort'][-1]
    contacts = [c for c in end['contacts'] if 'RedBlock' in c['roots']]
    return dict(source=end['source'], tcp=np.asarray(end['tcp'])[:3,3].tolist(), pads=end['pads'],
        source_geometry=end['source_geometry'], pad_geometry=end['pad_geometry'], contacts=contacts)


def examine(case, index, audit):
    folder = SOURCE/'cases'/NAME/f'attempt_{index}'
    files = [folder/name for name in ('route.json', 'span_inputs.npz', 'step.json', 'contacts.jsonl')]
    assert all(sha(p) == audit['identities'][str(p)] for p in files)
    plan = read(folder/'route.json')
    corners, center = geometry(case, plan)
    with np.load(folder/'span_inputs.npz') as arrays:
        points = arrays['world_points']
    nominal = sm.SE3(np.asarray(plan['context']['nominal']))
    midpoint = np.percentile(points, [5,95], axis=0).mean(axis=0)
    estimates = dict(nominal=nominal.t.tolist(), observed_midpoint=midpoint.tolist())
    errors = {k:(np.asarray(v)-center).tolist() for k,v in estimates.items()}
    rows = []
    for pose in poses(nominal):
        axis = pose['pose'].R[:,1]
        rows.append(dict(id=pose['id'], observed_span_m=span(points, axis),
            private_true_span_m=float(np.ptp(corners@axis))))
    record = read(folder/'execution/result.json')['records'][0]
    return dict(attempt=index, success=read(folder/'step.json')['success'], selected=plan['selected']['id'],
        error_type=(record.get('error') or {}).get('error_type'), poses=rows, estimates=estimates,
        private_errors_m=errors, observed_midpoint_delta_m=(midpoint-nominal.t).tolist(), closing=closing(folder))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    audit = read(SOURCE/'audits'/(NAME+'.json'))
    assert audit['passed'] and audit['manifest_sha256'] == sha(SOURCE/'manifest.json')
    assert all(sha(p) == h for p,h in audit['identities'].items())
    case = next(c for c in read(SOURCE/'manifest.json')['cases'] if c['item']['id'] == NAME)
    rows = [examine(case, index, audit) for index in (1,2,3)]
    save(ROOT/'result.json', dict(rows=rows, physical_attempts=0, model_calls=0, training_ready=False,
        limitation='Private engineering diagnosis only; no action labels or physical recovery evidence',
        identities={str(p):sha(p) for p in [Path(__file__), SOURCE/'audits'/(NAME+'.json')]}))
    for row in rows:
        print({k:v for k,v in row.items() if k not in ('closing', 'estimates')}, flush=True)


if __name__ == '__main__':
    main()
