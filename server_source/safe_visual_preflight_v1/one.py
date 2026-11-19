import argparse
import os
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import qualify
from sd_render import probe
from common import ROOT, read, save, sha, verify, visible


def render(case):
    key = str(case['item']['seed'])+'_'+case['item']['group']
    folder = ROOT/'renders'/key
    return probe(case['config'], folder)


def geometry(case):
    key = str(case['item']['seed'])+'_'+case['item']['group']
    report = read(ROOT/'renders'/key/'result.json')
    visibility = {k: report['visibility'][case['item'][k]] for k in ('source', 'destination')}
    row = dict(id=case['item']['id'], visibility=visibility, passed=False)
    if not all(visible(r) for r in visibility.values()):
        row['status'] = 'visibility_rejected'
    else:
        template = ROOT.parent/'ai_self_route_v1/cases/S0_962601_baseline/attempt_2/route.json'
        audit = read(ROOT.parent/'ai_self_route_v1/audit_962601.json')
        assert sha(template) == audit['identities'][str(template)]
        with patch.object(qualify, 'ROOT', ROOT):
            row.update(qualify.qualify(case, read(template)['context']))
    save(ROOT/'results'/(case['item']['id']+'.json'), row)
    print(row, flush=True)


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
