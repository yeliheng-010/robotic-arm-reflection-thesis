"""只读完整审计后的小批；产出候选输入与实际后果，不宣称正式训练就绪。"""
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
from f_common import read,save,sha
from nc_state import Branch
from live_telemetry import Recorder
from live_budget import apply_action
from action_check import check
from visual_requests_v2 import build
from policy import eligible,action,snapshot

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'natural_qualified_pilot_v1'


def bundle_for(case,result,index):
    step=result['steps'][index]
    branch=Branch(case['item'],result['steps'][0])
    for i in range(index):
        branch.remember(action(result['actions'][i]['action']))
        branch.append(result['steps'][i+1])
    folder=Path(step['session_path'])
    summary=read(folder/'observation_summary.json')
    recorder=Recorder()
    recorder.rows=read(folder/'telemetry.json')['rows']
    session=SimpleNamespace(folder=folder,step=step,recorder=recorder,
        record=read(step['result_path'])['records'][0])
    view=SimpleNamespace(paths=summary['paths'],sampler=SimpleNamespace(rows=summary['public'],private=summary['private']))
    return build(branch,session,view),summary,session.record


def collect(case):
    name=case['item']['id']
    audit=read(SOURCE/'audits'/(name+'.json'))
    assert audit['passed'] and audit['manifest_sha256']==sha(SOURCE/'manifest.json')
    assert all(sha(p)==h for p,h in audit['identities'].items())
    result=read(SOURCE/'cases'/name/'result.json')
    rows=[]
    for index,entry in enumerate(result['actions']):
        step,following=result['steps'][index:index+2]
        assert not step['success']
        bundle,summary,record=bundle_for(case,result,index)
        executed=action(entry['action'])
        check(executed,bundle['request'])
        assert apply_action(step['state'],executed)==following['state']
        allowed,reason=eligible(record)
        path=ROOT/'inputs'/name/f'decision_{index+1}.json'
        save(path,bundle)
        rows.append(dict(condition=name,seed=case['item']['seed'],group=case['item']['group'],
            snapshot_id=snapshot(case['item'],summary),input_path=str(path),input_sha256=sha(path),
            eligible_natural=allowed,private_eligibility_reason=reason,action=executed,
            successor=following,verified_recovery=allowed and following['success'],
            supervision_claim='executed_successor_only_not_optimal_or_causal'))
    return rows


def main():
    assert os.environ.get('SLURM_JOB_ID')
    tested=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    manifest,complete=read(SOURCE/'manifest.json'),read(SOURCE/'complete.json')
    assert complete['passed']
    rows=[row for case in manifest['cases'] for row in collect(case)]
    natural=[r for r in rows if r['eligible_natural']]
    recovered=[r for r in natural if r['verified_recovery']]
    summary=dict(decisions=len(rows),unique_natural_snapshots=len({r['snapshot_id'] for r in natural}),
        verified_natural_recoveries=len({r['snapshot_id'] for r in recovered}),
        correction_action_types=sorted({r['action']['id'] for r in recovered}),
        natural_seed_groups=sorted({r['seed'] for r in natural}),
        recovery_seed_groups=sorted({r['seed'] for r in recovered}),
        exclusions=dict(Counter(r['private_eligibility_reason'] for r in rows if not r['eligible_natural'])),
        tests=tested.testsRun,pilot_is_training_data=False,training_ready=False)
    save(ROOT/'inventory.json',dict(summary=summary,rows=rows,manifest_sha256=sha(SOURCE/'manifest.json'),
        identities={str(p):sha(p) for p in ROOT.glob('*.py')}))
    print(summary,flush=True)


if __name__=='__main__':
    main()
