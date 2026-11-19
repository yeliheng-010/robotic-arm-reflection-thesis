"""新数据独立审计入口，与历史 rc_audit 隔离。"""
import os
import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import sv_requests_v2
import sv_audit_replay
import sv_strategy_audit
from audit_v5 import audit_attempt
from sv_strategy_requests import build
from rc_audit_branch import replay
from collection_common import ROOT, PHYSICS, BRANCHES, read, save, sha, verify


def inspect(case):
    folder = PHYSICS/'cases'/case['item']['id']
    result = read(folder/'result.json')
    assert result['manifest_sha256'] == sha(PHYSICS/'manifest.json')
    assert result['status'] == 'completed' and set(result['methods']) == set(BRANCHES)
    first, observed = read(folder/'first/step.json'), read(folder/'first/observation_summary.json')
    cache, methods = {}, {}
    for method in BRANCHES:
        branch = read(folder/method/'result.json')
        assert branch['method'] == method
        methods[method] = replay(case, branch, first=first, first_view=observed, cache=cache)
    assert methods == result['methods']
    assert result['attempts'] == 1+sum(v['new_attempts'] for v in methods.values()) <= 7
    assert result['model_calls'] == 0
    return dict(id=case['item']['id'], attempts=result['attempts'], methods=methods,
        physical=[dict(path=p, geometry=v['geometry'], contact=v['contact']) for p,v in cache.items()])


def main():
    assert os.environ.get('SLURM_JOB_ID')
    name = sys.argv[1]
    case = next(c for c in verify(PHYSICS/'manifest.json')['cases'] if c['item']['id'] == name)
    with patch.object(sv_requests_v2, 'ROOT', PHYSICS), patch.object(sv_audit_replay, 'build', build), \
         patch.object(sv_strategy_audit, 'audit_attempt', audit_attempt):
        row = inspect(case)
    files = [p for p in (PHYSICS/'cases'/name).rglob('*') if p.is_file()]
    files += list(ROOT.glob('*.py'))
    save(PHYSICS/'audits'/(name+'.json'), dict(passed=True, row=row,
        manifest_sha256=sha(PHYSICS/'manifest.json'), identities={str(p):sha(p) for p in files}))
    print(dict(id=name, attempts=row['attempts'], audited=True), flush=True)


if __name__ == '__main__':
    main()
