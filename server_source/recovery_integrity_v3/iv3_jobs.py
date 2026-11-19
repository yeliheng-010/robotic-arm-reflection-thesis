"""仅执行从未启动条件；使用新日志保留上次审计错误。"""
import os
import sys
import subprocess
from pathlib import Path
from iv3_audit import BASE, ROOT
from collection_common import PHYSICS, read, sha, verify
from ig_policy import execution_mode
from rc_controller import run
sys.path.insert(0, str(ROOT.parent / 'collection_scale_v1'))
from sc_policy import shard_cases


def audit_or_reuse(case):
    name = case['item']['id']
    accepted = PHYSICS / 'audits' / (name+'.json')
    rejected = PHYSICS / 'audit_rejections' / (name+'.json')
    assert not (accepted.exists() and rejected.exists())
    if accepted.exists() or rejected.exists():
        value = verify(accepted if accepted.exists() else rejected)
        assert value['manifest_sha256'] == sha(PHYSICS / 'manifest.json')
        assert value['passed'] is accepted.exists()
        return 'reused_accepted' if accepted.exists() else 'reused_rejected'
    log = PHYSICS / ('integrity_v3_audit_'+name+'.log')
    with log.open('x', encoding='utf-8') as stream:
        subprocess.run([sys.executable, '-B', str(ROOT / 'iv3_audit.py'), name],
            stdout=stream, stderr=subprocess.STDOUT, check=True)
    return 'accepted' if accepted.exists() else 'rejected'


def process(case):
    folder = PHYSICS / 'cases' / case['item']['id']
    completed = (folder / 'result.json').exists() and read(folder / 'result.json')['status'] == 'completed'
    mode = execution_mode(folder_exists=folder.exists(), completed=completed)
    if mode == 'execute_new':
        run('collect_worker.py', [case['item']['id']], label=case['item']['id'])
    disposition = audit_or_reuse(case)
    print(dict(id=case['item']['id'], execution=mode, disposition=disposition), flush=True)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify(ROOT / 'source_manifest.json')
    verify(BASE / 'source_manifest.json')
    manifest = verify(PHYSICS / 'manifest.json')
    cases = manifest['cases']
    if sys.argv[1] == 'shard':
        cases = shard_cases(cases, index=int(os.environ['SLURM_ARRAY_TASK_ID']))
    else:
        assert sys.argv[1] == 'resume' and manifest['batch'] == 6
    for case in cases:
        process(case)
    verify(ROOT / 'source_manifest.json')


if __name__ == '__main__':
    main()
