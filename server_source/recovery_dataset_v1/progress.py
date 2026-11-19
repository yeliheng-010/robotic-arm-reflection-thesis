"""仅盘点已完成逐条件审计的文本证据；不替代最终完整数据审计。"""
import os
from pathlib import Path
from unittest.mock import patch
import rc_review
from rc_gate import summarize, assess
from collection_common import ROOT as COLLECTION, BRANCHES, read, save, sha

ROOT = Path(__file__).resolve().parent


def collect(case, audit):
    def checked(path):
        path = Path(path)
        assert sha(path)==audit['identities'][str(path)]
        return read(path)

    folder = Path(audit['row']['physical'][0]['path']).parent
    rows = []
    with patch.object(rc_review,'read',checked):
        for method in BRANCHES:
            rows.extend(rc_review.decisions(case,checked(folder/method/'result.json')))
    return rows


def main():
    assert os.environ.get('SLURM_JOB_ID')
    rows, conditions, identities = [], [], {}
    for path in sorted(COLLECTION.glob('batches/*/physics/manifest.json')):
        manifest = read(path)
        for case in manifest['cases']:
            audit_path = path.parent/'audits'/(case['item']['id']+'.json')
            if not audit_path.exists():
                continue
            audit = read(audit_path)
            assert audit['passed'] and audit['manifest_sha256']==sha(path)
            rows.extend(collect(case,audit))
            conditions.append(dict(id=case['item']['id'],attempts=audit['row']['attempts']))
            identities[str(audit_path)] = sha(audit_path)
    summary = summarize(rows)
    output = dict(partial=True,audited_conditions=len(conditions),
        attempts=sum(r['attempts'] for r in conditions),summary=summary,gate=assess(summary),
        identities=identities,limitation='Text identity checked; full sensor/image recheck belongs to final export')
    save(ROOT/'progress'/('job_'+os.environ['SLURM_JOB_ID']+'.json'),output)
    print(dict(conditions=len(conditions),summary=summary),flush=True)


if __name__=='__main__':
    main()
