"""每阶段复核工程完整性；物理成功率不作调参或删样本依据。"""
import argparse
import json
from stability.collection_status import atomic
from expand.design import ROOT
from expand.run import entries,SHARDS
from expand.report import main


def check(phase):
    expected=entries(phase)
    rows=[]
    for shard in range(SHARDS):
        saved=json.loads((ROOT/'stages'/phase/f'shard_{shard}'/'progress.json').read_text())
        assert saved['status']=='completed'
        assert saved['completed']==saved['expected']==sum(i%SHARDS==shard for i in range(len(expected)))
        rows.extend(saved['rows'])
    assert {r['id'] for r in rows}=={r['id'] for _,r in expected}
    report=main()
    if phase in ('qual_smoke','qualification'):
        assert any(r['eligible'] for r in rows), 'No eligible scene; preserve and stop'
    else:
        assert any(r['executed'] for r in rows), 'No executed loop smoke'
        assert not any(r['service_errors'] or r['invalid'] for r in rows)
    value=dict(status='ready',stage=phase,accounted=len(rows),success_rate_used_as_gate=False,
               protocol_sha256=report['protocol_sha256'],training_approved=0)
    atomic(ROOT/f'gate_{phase}.json',value)
    print(json.dumps(value))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('qual_smoke','qualification','loop_smoke'))
    args=parser.parse_args()
    try:
        check(args.phase)
    except BaseException as error:
        atomic(ROOT/f'gate_{args.phase}_failure.json',dict(status='failed',error=repr(error)))
        raise
