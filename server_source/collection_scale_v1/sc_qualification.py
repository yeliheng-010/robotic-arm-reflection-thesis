import os
import sys
import subprocess
from pathlib import Path
from reflection.__main__ import bootstrap
bootstrap()
from collection_common import ROOT as COLLECTION, QUAL, read, save, sha, verify
from rc_qualification import prepare as prepare_cases
from sc_policy import shard_cases

ROOT = Path(__file__).resolve().parent


def prepare():
    prepare_cases()
    paths = [*ROOT.glob('*.py'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md',
        COLLECTION/'qual_one_v2.py', COLLECTION/'qualification_resume_v2.py']
    save(QUAL/'scale_revision.json', dict(identities={str(p):sha(p) for p in paths},
        change='disjoint_seed_qualification_shards_only', original_protocol_sha256=sha(COLLECTION/'protocol.json')))


def run(mode, name):
    with (QUAL/(mode+'_'+name+'.log')).open('x') as log:
        subprocess.run([sys.executable,'-B',str(COLLECTION/'qual_one_v2.py'),mode,name],
            stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)


def shard():
    index = int(os.environ['SLURM_ARRAY_TASK_ID'])
    cases = shard_cases(verify(QUAL/'manifest.json')['cases'],index=index)
    verify(QUAL/'scale_revision.json')
    seen, identities = set(), {}
    for case in cases:
        name = case['item']['id']
        key = case['item']['seed'],case['item']['group']
        if key not in seen:
            run('render',name)
            seen.add(key)
        run('geometry',name)
        path = QUAL/'results'/(name+'.json')
        row = read(path)
        assert row['id']==name
        identities[str(path)] = sha(path)
        print(dict(id=name,passed=row['passed']),flush=True)
    verify(QUAL/'manifest.json')
    save(QUAL/f'shard_{index}.json',dict(passed=True,cases=[c['item']['id'] for c in cases],identities=identities))


def merge():
    manifest = verify(QUAL/'manifest.json')
    revision = verify(QUAL/'scale_revision.json')
    shards = [verify(QUAL/f'shard_{i}.json') for i in range(4)]
    found = [name for shard in shards for name in shard['cases']]
    assert len(found)==len(set(found)) and set(found)=={c['item']['id'] for c in manifest['cases']}
    rows = [read(QUAL/'results'/(c['item']['id']+'.json')) for c in manifest['cases']]
    for row in rows:
        if 'path' in row:
            assert sha(row['path'])==row['sha256']
    paths = [QUAL/'scale_revision.json',*list((QUAL/'results').glob('*.json')),*list((QUAL/'plans').glob('*.json'))]
    identities = dict(revision['identities'])
    identities.update({str(p):sha(p) for p in paths})
    save(QUAL/'result.json',dict(rows=rows,physical_attempts=0,model_calls=0,identities=identities,
        manifest_sha256=sha(QUAL/'manifest.json')))


if __name__=='__main__':
    assert os.environ.get('SLURM_JOB_ID')
    dict(prepare=prepare,shard=shard,merge=merge)[sys.argv[1]]()
