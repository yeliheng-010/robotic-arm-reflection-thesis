import argparse
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import span_qualify
from qualification_data import derive
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case_id')
    name = parser.parse_args().case_id
    manifest = read(ROOT/'manifest.json')
    assert all(sha(p) == h for p,h in manifest['identities'].items())
    case = next(c for c in manifest['cases'] if c['item']['id'] == name)
    key = str(case['item']['seed'])+'_'+case['item']['group']
    folder = ROOT.parent/'safe_visual_preflight_v1/renders'/key
    if case['item']['group'] == 'baseline':
        folder = ROOT.parent/'natural_observable_preflight_v1/renders/962801_baseline'
    calibration = read(folder/'result.json')
    assert sha(folder/'sensor.npz') == calibration['sensor_sha256']
    projection, points, noise = derive(folder, case['config'], item=case['item'], calibration=calibration)
    row = dict(id=name, passed=False, projection=projection, qualification_noise=noise)
    if not all(r['passed'] for r in projection.values()):
        row['status'] = 'grounding_projection_rejected'
    else:
        template = ROOT.parent/'ai_self_route_v1/cases/S0_962601_baseline/attempt_2/route.json'
        audit = read(ROOT.parent/'ai_self_route_v1/audit_962601.json')
        assert sha(template) == audit['identities'][str(template)]
        with patch.object(span_qualify, 'ROOT', ROOT):
            row.update(span_qualify.qualify(case, read(template)['context'], points))
    save(ROOT/'results'/(name+'.json'), row)


if __name__ == '__main__':
    main()
