"""后续批次按完整种子并行；同条件的三个分支始终在同一进程。"""
import os
import sys
from reflection.__main__ import bootstrap
bootstrap()
from collection_common import PHYSICS, read, save, sha, verify
from rc_prepare import main as prepare
from rc_controller import run
from rc_review import main as review
from sc_policy import shard_cases


def shard():
    index = int(os.environ['SLURM_ARRAY_TASK_ID'])
    manifest = verify(PHYSICS/'manifest.json')
    cases = shard_cases(manifest['cases'],index=index)
    rows = []
    for case in cases:
        name = case['item']['id']
        run('collect_worker.py',[name],label=name)
        run('collect_audit.py',[name],label='audit_'+name)
        audit = verify(PHYSICS/'audits'/(name+'.json'))
        assert audit['passed']
        rows.append(audit['row'])
        print(dict(id=name,attempts=rows[-1]['attempts'],audited=True),flush=True)
    save(PHYSICS/f'shard_{index}.json',dict(passed=True,rows=rows,
        manifest_sha256=sha(PHYSICS/'manifest.json')))


def merge():
    manifest = verify(PHYSICS/'manifest.json')
    shards = [read(PHYSICS/f'shard_{i}.json') for i in range(4)]
    assert all(r['passed'] and r['manifest_sha256']==sha(PHYSICS/'manifest.json') for r in shards)
    rows = [row for shard in shards for row in shard['rows']]
    names = [r['id'] for r in rows]
    assert len(names)==len(set(names)) and set(names)=={c['item']['id'] for c in manifest['cases']}
    for row in rows:
        audit = verify(PHYSICS/'audits'/(row['id']+'.json'))
        assert audit['passed'] and audit['row']==row
    attempts = sum(r['attempts'] for r in rows)
    assert attempts<=manifest['max_attempts']
    save(PHYSICS/'complete.json',dict(passed=True,rows=rows,attempts=attempts,model_calls=0,
        manifest_sha256=sha(PHYSICS/'manifest.json'),training_ready=False))
    review()


if __name__=='__main__':
    assert os.environ.get('SLURM_JOB_ID')
    dict(prepare=prepare,shard=shard,merge=merge)[sys.argv[1]]()
