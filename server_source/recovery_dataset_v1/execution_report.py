"""将执行尝试、真正启动运动和规划拒绝分列。"""
import os
from pathlib import Path
from collections import Counter
from collection_common import ROOT as COLLECTION, read, save, sha, verify
from policy import eligible

ROOT = Path(__file__).resolve().parent


def attempts(case, audit):
    rows = []
    for entry in audit['row']['physical']:
        folder = Path(entry['path'])
        step, bridge = read(folder/'step.json'), read(folder/'bridge.json')
        record = read(step['result_path'])['records'][0]
        natural, reason = (False,'success') if step['success'] else eligible(record)
        rows.append(dict(path=str(folder),group=case['item']['group'],source=case['item']['source'],
            success=step['success'],motion_started=any(p['executed'] for p in bridge['planners']),
            natural_failure=natural,category=reason))
    assert len(rows)==audit['row']['attempts']
    return rows


def main():
    assert os.environ.get('SLURM_JOB_ID')
    rows, conditions, identities = [], [], {}
    for manifest_path in sorted(COLLECTION.glob('batches/*/physics/manifest.json')):
        if not (manifest_path.parent/'complete.json').exists():
            continue
        manifest = verify(manifest_path)
        for case in manifest['cases']:
            path = manifest_path.parent/'audits'/(case['item']['id']+'.json')
            audit = verify(path)
            assert audit['passed'] and audit['manifest_sha256']==sha(manifest_path)
            rows.extend(attempts(case,audit))
            conditions.append(dict(id=case['item']['id'],group=case['item']['group'],
                methods=audit['row']['methods']))
            identities[str(path)] = sha(path)
    assert rows
    summary = {group:dict(attempts=sum(r['group']==group for r in rows),
        motion_started=sum(r['group']==group and r['motion_started'] for r in rows),
        categories=dict(Counter(r['category'] for r in rows if r['group']==group)))
        for group in ('baseline','varied_noisy')}
    save(ROOT/'execution'/('job_'+os.environ['SLURM_JOB_ID']+'.json'),dict(summary=summary,rows=rows,
        conditions=conditions,identities=identities,
        limitation='exploration_branches_are_not_equal_budget_AI_performance_comparisons'))
    print(summary,flush=True)


if __name__=='__main__':
    main()
