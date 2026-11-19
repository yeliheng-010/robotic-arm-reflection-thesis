import os
import sys
import subprocess
from collection_common import ROOT, QUAL, read, save, sha, verify


def run(mode, name):
    with (QUAL/(mode+'_'+name+'_v2.log')).open('x') as log:
        subprocess.run([sys.executable, '-B', str(ROOT/'qual_one_v2.py'), mode, name],
            stdout=log, stderr=subprocess.STDOUT, check=True, timeout=900)


def rendered(case):
    folder = QUAL/'renders'/(str(case['item']['seed'])+'_'+case['item']['group'])
    if not folder.exists():
        run('render', case['item']['id'])
    result = read(folder/'result.json')
    assert sha(folder/'sensor.npz') == result['sensor_sha256']


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify(QUAL/'manifest.json')
    files = [ROOT/'qual_one_v2.py', ROOT/'qualification_resume_v2.py', ROOT/'qualify_resume_v2.sbatch']
    save(QUAL/'revision_v2.json', dict(fix='separate_project_reference_and_batch_output_paths',
        manifest_sha256=sha(QUAL/'manifest.json'), physical_attempts=0, model_calls=0,
        identities={str(p):sha(p) for p in files}))
    rows, seen = [], set()
    for case in manifest['cases']:
        name = case['item']['id']
        key = case['item']['seed'], case['item']['group']
        if key not in seen:
            rendered(case)
            seen.add(key)
        path = QUAL/'results'/(name+'.json')
        if not path.exists():
            run('geometry',name)
        row = read(path)
        assert row['id'] == name
        if 'path' in row:
            assert sha(row['path']) == row['sha256']
        rows.append(row)
        print(dict(id=name, passed=row['passed'], status=row['status']), flush=True)
    verify(QUAL/'manifest.json')
    verify(QUAL/'revision_v2.json')
    files += [QUAL/'revision_v2.json', *list((QUAL/'results').glob('*.json')), *list((QUAL/'plans').glob('*.json'))]
    save(QUAL/'result.json', dict(rows=rows, model_calls=0, physical_attempts=0,
        identities={str(p):sha(p) for p in files}, manifest_sha256=sha(QUAL/'manifest.json')))


if __name__ == '__main__':
    main()
