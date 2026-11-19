"""复用完整审计和完整已执行轨迹；只执行从未启动的条件。"""
import os
import sys
import subprocess
from pathlib import Path
from reflection.__main__ import bootstrap
bootstrap()
from collection_common import PHYSICS, read, save, sha, verify
from rc_controller import run
from ig_policy import execution_mode

ROOT = Path(__file__).resolve().parent
SCALE = ROOT.parent / 'collection_scale_v1'
sys.path.insert(0, str(SCALE))
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
    log = PHYSICS / ('integrity_audit_'+name+'.log')
    with log.open('x', encoding='utf-8') as stream:
        subprocess.run([sys.executable, '-B', str(ROOT / 'ig_audit.py'), name],
            stdout=stream, stderr=subprocess.STDOUT, check=True)
    return 'accepted' if accepted.exists() else 'rejected'


def process(case):
    name = case['item']['id']
    folder = PHYSICS / 'cases' / name
    completed = (folder / 'result.json').exists() and read(folder / 'result.json')['status'] == 'completed'
    mode = execution_mode(folder_exists=folder.exists(), completed=completed)
    if mode == 'execute_new':
        run('collect_worker.py', [name], label=name)
    disposition = audit_or_reuse(case)
    print(dict(id=name, execution=mode, disposition=disposition), flush=True)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify(ROOT / 'source_manifest.json')
    manifest = verify(PHYSICS / 'manifest.json')
    cases = manifest['cases']
    if sys.argv[1] == 'shard':
        cases = shard_cases(cases, index=int(os.environ['SLURM_ARRAY_TASK_ID']))
    else:
        assert sys.argv[1] == 'resume' and manifest['batch'] == 4
    for case in cases:
        process(case)
    verify(ROOT / 'source_manifest.json')


if __name__ == '__main__':
    main()
