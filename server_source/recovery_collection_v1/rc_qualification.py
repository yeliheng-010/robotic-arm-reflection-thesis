"""复用冻结资格算法；每项独立进程，避免累计内存。"""
import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import nc_prepare
from collection_common import ROOT, PARENT, BATCH, QUAL, seeds, split, read, save, sha, verify

PREFLIGHT = PARENT/'natural_top_preflight_v1'


def prepare():
    protocol = verify(ROOT/'protocol.json')
    previous = verify(PREFLIGHT/'manifest.json')
    with patch.object(nc_prepare, 'SEEDS', seeds(BATCH)):
        cases = nc_prepare.cases()
    cases = [c for c in cases if c['item']['group']=='varied_noisy' or c['item']['seed']==seeds(BATCH)[0]]
    for case in cases:
        case['item']['id'] = 'R'+case['item']['id'][1:]
        case['item']['split'] = split(case['item']['seed'])
    identities = dict(previous['identities'], **protocol['identities'])
    identities[str(ROOT/'protocol.json')] = sha(ROOT/'protocol.json')
    save(QUAL/'manifest.json', dict(cases=cases, seeds=list(seeds(BATCH)), identities=identities,
        physical_attempts=0, model_calls=0, batch=BATCH, training_ready=False))
    return cases


def run(mode, name):
    with (QUAL/(mode+'_'+name+'.log')).open('x') as log:
        subprocess.run([sys.executable, '-B', str(ROOT/'rc_qual_one.py'), mode, name],
            stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    cases = prepare()
    seen, rows = set(), []
    for case in cases:
        key = case['item']['seed'], case['item']['group']
        name = case['item']['id']
        if key not in seen:
            run('render', name)
            seen.add(key)
        run('geometry', name)
        row = read(QUAL/'results'/(name+'.json'))
        rows.append(row)
        print(dict(id=name, passed=row['passed'], status=row['status']), flush=True)
    verify(QUAL/'manifest.json')
    files = [*list((QUAL/'results').glob('*.json')), *list((QUAL/'plans').glob('*.json'))]
    save(QUAL/'result.json', dict(rows=rows, model_calls=0, physical_attempts=0,
        identities={str(p):sha(p) for p in files}, manifest_sha256=sha(QUAL/'manifest.json')))


if __name__ == '__main__':
    main()
