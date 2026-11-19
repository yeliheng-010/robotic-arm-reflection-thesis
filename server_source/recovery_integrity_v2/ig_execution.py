"""同时盘点接受与拒绝条件的真实执行消耗，不隐去安全拒绝。"""
import os
import sys
from pathlib import Path
from collections import Counter
from reflection.__main__ import bootstrap
bootstrap()
from collection_common import ROOT as COLLECTION, read, save, sha, verify

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'recovery_dataset_v1'))
from execution_report import attempts


def case_attempts(case, physics):
    name = case['item']['id']
    folder = physics / 'cases' / name
    result = read(folder / 'result.json')
    steps = {}
    for branch in result['methods']:
        for step in read(folder / branch / 'result.json')['ledger']['steps']:
            assert steps.setdefault(step['session_path'], step) == step
    accepted = (physics / 'audits' / (name+'.json')).exists()
    rejected = (physics / 'audit_rejections' / (name+'.json')).exists()
    assert accepted != rejected
    path = physics / ('audits' if accepted else 'audit_rejections') / (name+'.json')
    audit = verify(path)
    assert audit['passed'] is accepted
    proxy = dict(row=dict(attempts=result['attempts'], physical=[dict(path=p) for p in steps]))
    rows = attempts(case, proxy)
    for row in rows:
        row['condition'] = name
        row['condition_audit_accepted'] = accepted
    return rows, path


def summarize(rows):
    return dict(attempts=len(rows), motion_started=sum(r['motion_started'] for r in rows),
        accepted_condition_attempts=sum(r['condition_audit_accepted'] for r in rows),
        rejected_condition_attempts=sum(not r['condition_audit_accepted'] for r in rows),
        raw_task_success_ignores_safety=sum(r['success'] for r in rows),
        raw_categories=dict(Counter(r['category'] for r in rows)))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify(ROOT / 'source_manifest.json')
    rows, identities = [], {}
    for inventory in sorted(COLLECTION.glob('batches/*/physics/inventory.json')):
        verify(inventory)
        physics = inventory.parent
        manifest = verify(physics / 'manifest.json')
        for case in manifest['cases']:
            found, path = case_attempts(case, physics)
            rows.extend(found)
            identities[str(path)] = sha(path)
        identities[str(inventory)] = sha(inventory)
    assert rows
    summary = {g: summarize([r for r in rows if r['group'] == g]) for g in ('baseline', 'varied_noisy')}
    save(ROOT / 'execution' / ('job_'+os.environ['SLURM_JOB_ID']+'.json'), dict(summary=summary,
        rows=rows, identities=identities, limitation='Exploration consumption, not equal-budget AI recovery performance'))
    print(summary, flush=True)


if __name__ == '__main__':
    main()
