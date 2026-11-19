"""批次输出与项目参考路径分开，沿用原资格算法与阈值。"""
import os
import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from sd_render import probe
from qualification_data import derive
from common import visible
import span_qualify
from collection_common import PARENT, QUAL, read, save, sha, verify


def reference():
    path = PARENT/'ai_self_route_v1/cases/S0_962601_baseline/attempt_2/route.json'
    audit = read(PARENT/'ai_self_route_v1/audit_962601.json')
    assert audit['passed'] and sha(path) == audit['identities'][str(path)]
    return read(path)['context']


def geometry(case):
    folder = QUAL/'renders'/(str(case['item']['seed'])+'_'+case['item']['group'])
    report = read(folder/'result.json')
    assert sha(folder/'sensor.npz') == report['sensor_sha256']
    visibility = {k:report['visibility'][case['item'][k]] for k in ('source','destination')}
    projected, points, noise = derive(folder, case['config'], item=case['item'], calibration=report)
    row = dict(id=case['item']['id'], visibility=visibility, projection=projected,
        qualification_noise=noise, passed=False)
    if not all(visible(r) for r in visibility.values()):
        row['status'] = 'visibility_rejected'
    elif not all(r['passed'] for r in projected.values()):
        row['status'] = 'grounding_projection_rejected'
    elif len(points) < 64:
        row['status'] = 'insufficient_noisy_target_points'
    else:
        with patch.object(span_qualify, 'ROOT', QUAL):
            row.update(span_qualify.qualify(case, reference(), points))
    save(QUAL/'results'/(case['item']['id']+'.json'), row)
    print(dict(id=row['id'], passed=row['passed'], status=row['status']), flush=True)


if __name__ == '__main__':
    assert os.environ.get('SLURM_JOB_ID')
    mode, name = sys.argv[1:]
    assert mode in ('render','geometry')
    case = next(c for c in verify(QUAL/'manifest.json')['cases'] if c['item']['id']==name)
    if mode == 'geometry':
        geometry(case)
    else:
        probe(case['config'], QUAL/'renders'/(str(case['item']['seed'])+'_'+case['item']['group']))
    verify(QUAL/'manifest.json')
