"""复用已审计旧轨迹验证新采集/审计接线，零新增物理和模型调用。"""
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import rc_branch
import sv_requests_v2
import sv_audit_replay
import sv_strategy_audit
from nc_branch import persist
from live_telemetry import Recorder
from audit_v5 import audit_attempt
from sv_strategy_requests import build
from rc_audit_branch import replay
from f_common import read, save, sha

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_safe_visual_loop_v1'


def session(step):
    folder = Path(step['session_path'])
    recorder = Recorder()
    recorder.rows = read(folder/'telemetry.json')['rows']
    return SimpleNamespace(folder=folder, step=step, index=step['index'], recorder=recorder,
        record=read(step['result_path'])['records'][0])


def observed(summary):
    return SimpleNamespace(paths=summary['paths'], sampler=SimpleNamespace(rows=summary['public'],
        private=summary['private'], attempt=summary['public'][0]['attempt'], budget=SimpleNamespace(count=1)),
        summary=lambda:summary)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    name = 'A0_962905_varied_noisy'
    audit = read(SOURCE/'audits'/(name+'.json'))
    assert audit['passed'] and all(sha(p)==h for p,h in audit['identities'].items())
    case = next(c for c in read(SOURCE/'manifest.json')['cases'] if c['item']['id']==name)
    prior = read(SOURCE/'cases'/name/'fixed_rule/result.json')
    first, following = [session(s) for s in prior['ledger']['steps']]
    summaries = [read(v['path']) for v in prior['views']]
    views = [observed(v) for v in summaries]

    def next_attempt(case, branch, *, action, folder, stack):
        assert action == prior['decisions'][0]['action']
        branch.append(following.step)
        return following

    target = ROOT/'replay_check'/('job_'+os.environ['SLURM_JOB_ID'])
    with patch.object(sv_requests_v2,'ROOT',SOURCE), patch.object(rc_branch,'View',side_effect=views), \
         patch.object(rc_branch,'next_attempt',next_attempt):
        result = rc_branch.run(case,first,shared=views[0],method='top_then_slow',folder=target)
    assert result['success'] and result['new_attempts']==1 and len(result['decisions'])==1
    with patch.object(sv_requests_v2,'ROOT',SOURCE), patch.object(sv_audit_replay,'build',build), \
         patch.object(sv_strategy_audit,'audit_attempt',audit_attempt):
        checked = replay(case,result,first=first.step,first_view=summaries[0],cache={})
    assert checked['success']
    paths = [Path(__file__), SOURCE/'audits'/(name+'.json'), *list((ROOT.parent/'recovery_collection_v1').glob('*.py'))]
    save(target/'verification.json',dict(passed=True,new_physical_attempts=0,model_calls=0,
        historical_source=name,identities={str(p):sha(p) for p in paths}))
    print(dict(passed=True,new_physical_attempts=0,model_calls=0),flush=True)


if __name__ == '__main__':
    main()
