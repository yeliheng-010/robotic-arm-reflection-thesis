import os
import subprocess
import sys
from common import ROOT, read, save, sha, verify
from nc_common import status

PREVIOUS = ROOT.parent/'natural_observable_preflight_v1'


def run(mode, case):
    name = mode+'_'+case['item']['id']
    status(ROOT/'status.json', dict(stage=name))
    with (ROOT/(name+'.log')).open('x') as log:
        subprocess.run([sys.executable, '-B', str(ROOT/'one.py'), mode, case['item']['id']],
            stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)


def baseline(case):
    manifest = read(PREVIOUS/'manifest.json')
    assert all(sha(p) == h for p,h in manifest['identities'].items())
    old = next(c for c in manifest['cases'] if c['item']['group'] == 'baseline' and c['item']['source'] == case['item']['source'])
    assert {k:v for k,v in old['config'].items() if k != 'seed'} == {k:v for k,v in case['config'].items() if k != 'seed'}
    path = PREVIOUS/'results'/(old['item']['id']+'.json')
    row = read(path)
    complete = read(PREVIOUS/'result.json')
    assert row in complete['rows'] and row['passed'] and sha(row['path']) == row['sha256']
    row.update(id=case['item']['id'], reused_from=str(path), reused_result_sha256=sha(path),
        baseline_config_identical_except_seed=True)
    save(ROOT/'results'/(case['item']['id']+'.json'), row)
    return row


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    save(ROOT/'started.json', dict(job=os.environ['SLURM_JOB_ID']))
    seen, rows = set(), []
    for case in manifest['cases']:
        key = case['item']['seed'], case['item']['group']
        if case['item']['group'] == 'baseline':
            row = baseline(case)
        else:
            if key not in seen:
                run('render', case)
                seen.add(key)
            run('geometry', case)
            row = read(ROOT/'results'/(case['item']['id']+'.json'))
        rows.append(row)
        print(dict(id=row['id'], passed=row['passed'], status=row['status']), flush=True)
    verify()
    save(ROOT/'result.json', dict(rows=rows, physical_attempts=0, model_calls=0, training_ready=False,
        limitation='Conditional on visibility and finite reference planning; not physical success'))
    status(ROOT/'status.json', dict(stage='completed', passed=sum(r['passed'] for r in rows)))


if __name__ == '__main__':
    main()
