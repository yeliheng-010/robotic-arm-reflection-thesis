"""只从完整独立审计导出后果，不把探索提议当正确标签。"""
import os
from pathlib import Path
from policy import eligible, snapshot
from check_input import public
from sv_strategy_actions import apply
from rc_gate import summarize, assess
from collection_common import ROOT, PHYSICS, BRANCHES, read, save, sha, verify


def decisions(case, branch):
    rows = []
    summaries = [read(r['path']) for r in branch['views']]
    for index, event in enumerate(branch['decisions']):
        before, following = branch['ledger']['steps'][index:index+2]
        state, strategy = apply(before, event['action'])
        assert not before['success'] and state == following['state'] and strategy == following['strategy']
        assert sha(event['input_path']) == event['input_sha256']
        public(read(event['input_path'])['request'])
        allowed, reason = eligible(read(before['result_path'])['records'][0])
        rows.append(dict(snapshot_id=snapshot(case['item'], summaries[index]), seed=case['item']['seed'],
            split=case['item']['split'], source=case['item']['source'], condition=case['item']['id'],
            branch=branch['method'], action=event['action'], input_path=event['input_path'],
            input_sha256=event['input_sha256'], before=before, successor=following,
            eligible_natural=allowed, private_eligibility_reason=reason,
            verified_recovery=bool(allowed and following['success']),
            claim='verified_corrective_reset_execution_not_optimal_or_causal'))
    return rows


def collect(case):
    name = case['item']['id']
    audit = verify(PHYSICS/'audits'/(name+'.json'))
    assert audit['passed'] and audit['manifest_sha256'] == sha(PHYSICS/'manifest.json')
    rows, stops = [], []
    for method in BRANCHES:
        branch = read(PHYSICS/'cases'/name/method/'result.json')
        rows.extend(decisions(case, branch))
        if branch['success']:
            ref = branch['success_input']
            assert sha(ref['input_path']) == ref['input_sha256']
            summary = read(branch['views'][-1]['path'])
            stops.append(dict(ref, snapshot_id=snapshot(case['item'], summary), seed=case['item']['seed'],
                split=case['item']['split'], action=dict(id='STOP', args={}), condition=name))
    return rows, stops


def main():
    assert os.environ.get('SLURM_JOB_ID') and read(PHYSICS/'complete.json')['passed']
    manifest = verify(PHYSICS/'manifest.json')
    rows, stops = [], []
    for case in manifest['cases']:
        decisions_found, success = collect(case)
        rows.extend(decisions_found)
        stops.extend(success)
    summary = summarize(rows)
    paths = [PHYSICS/'manifest.json', PHYSICS/'complete.json', *list((PHYSICS/'audits').glob('*.json'))]
    save(PHYSICS/'inventory.json', dict(summary=summary, gate=assess(summary), rows=rows, stops=stops,
        identities={str(p):sha(p) for p in paths}, qualification_proposed=len(manifest['qualification_rows']),
        qualification_passed=len(manifest['cases']), model_calls=0))
    print(dict(summary=summary, gate=assess(summary)), flush=True)


if __name__ == '__main__':
    main()
