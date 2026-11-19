import os
import unittest
from pathlib import Path
from itertools import product
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from route_audit_v3 import rebuild
from f_common import read, save, sha
from top_fit import estimate

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'natural_span_pilot_v1'


def compare(case, folder, audit):
    assert sha(folder/'span_inputs.npz') == audit['identities'][str(folder/'span_inputs.npz')]
    with np.load(folder/'span_inputs.npz') as arrays:
        estimate_value = estimate(arrays['world_points'])
    row = dict(id=case['item']['id'], attempt=folder.name, estimate=estimate_value,
        prior_success=read(folder/'step.json')['success'])
    if not estimate_value['available'] or case['item']['source'] != 'RedBlock':
        return row
    plan = read(folder/'route.json')
    flow = rebuild(case, plan)
    geom = flow.env.mj_model.geom('red_block').id
    data, model = flow.env.mj_data, flow.env.mj_model
    center = data.geom_xpos[geom]
    vertices = np.array(list(product((-1.,1.), repeat=3)))*model.geom_size[geom]
    vertices = vertices@data.geom_xmat[geom].reshape(3,3).T+center
    row['private_diagnostic'] = dict(estimated_center_error_m=(np.array(estimate_value['center'])-center).tolist(),
        true_width_at_estimated_axis_m=float(np.ptp(vertices@estimate_value['closing_axis'])),
        true_dimensions_m=(2*model.geom_size[geom]).tolist(), nominal_error_m=(np.array(plan['context']['nominal'])[:3,3]-center).tolist())
    return row


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'result.json').exists()
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    manifest = read(SOURCE/'manifest.json')
    rows, identities = [], {}
    for case in manifest['cases']:
        name = case['item']['id']
        audit_path = SOURCE/'audits'/(name+'.json')
        audit = read(audit_path)
        assert audit['passed'] and audit['manifest_sha256'] == sha(SOURCE/'manifest.json')
        assert all(sha(p) == h for p,h in audit['identities'].items())
        identities[str(audit_path)] = sha(audit_path)
        for folder in sorted((SOURCE/'cases'/name).glob('attempt_*')):
            rows.append(compare(case, folder, audit))
    identities.update({str(p):sha(p) for p in ROOT.iterdir() if p.suffix in ('.py','.md','.sbatch')})
    save(ROOT/'result.json', dict(rows=rows, tests=tested.testsRun, physical_attempts=0, model_calls=0,
        training_ready=False, identities=identities))
    for row in rows:
        print(row, flush=True)


if __name__ == '__main__':
    main()
