import argparse
import os
from reflection.__main__ import bootstrap
bootstrap()
from sd_render import probe
from common import ROOT, read, save, sha, verify, visible
from qualification_data import derive
from span_qualify import qualify


def render(case):
    key = str(case['item']['seed'])+'_'+case['item']['group']
    return probe(case['config'], ROOT/'renders'/key)


def geometry(case):
    key = str(case['item']['seed'])+'_'+case['item']['group']
    folder = ROOT/'renders'/key
    report = read(folder/'result.json')
    assert sha(folder/'sensor.npz') == report['sensor_sha256']
    visibility = {k: report['visibility'][case['item'][k]] for k in ('source','destination')}
    projected, points, noise = derive(folder, case['config'], item=case['item'], calibration=report)
    row = dict(id=case['item']['id'], visibility=visibility, projection=projected, qualification_noise=noise, passed=False)
    if not all(visible(r) for r in visibility.values()):
        row['status'] = 'visibility_rejected'
    elif not all(r['passed'] for r in projected.values()):
        row['status'] = 'grounding_projection_rejected'
    elif len(points) < 64:
        row['status'] = 'insufficient_noisy_target_points'
    else:
        template = ROOT.parent/'ai_self_route_v1/cases/S0_962601_baseline/attempt_2/route.json'
        audit = read(ROOT.parent/'ai_self_route_v1/audit_962601.json')
        assert sha(template) == audit['identities'][str(template)]
        row.update(qualify(case, read(template)['context'], points))
    save(ROOT/'results'/(case['item']['id']+'.json'), row)
    print(dict(id=row['id'], passed=row['passed'], status=row['status']), flush=True)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['render', 'geometry'])
    parser.add_argument('case_id')
    args = parser.parse_args()
    case = next(c for c in verify()['cases'] if c['item']['id'] == args.case_id)
    (render if args.mode == 'render' else geometry)(case)
    verify()


if __name__ == '__main__':
    main()
