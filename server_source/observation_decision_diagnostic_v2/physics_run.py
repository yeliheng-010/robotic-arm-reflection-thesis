"""四卡固定快照分片，已有冒烟只读复核；部分输出禁止重跑。"""
import argparse
import os
import subprocess
from od_common import ROOT,SHARDS,SMOKE_CASES,verify,read,save,sha
from od_physics_audit import audit_case


def run(phase,shard):
    manifest=verify()
    gate=read(ROOT/('gate_physics_smoke.json' if phase=='batch' else 'gate_model.json'))
    assert gate['passed'] and gate['manifest_sha256']==sha(ROOT/'manifest.json')
    order=list(enumerate(manifest['cases']))
    if phase=='smoke':
        order=order[:SMOKE_CASES]
    directory=ROOT/'stages'/phase/f'shard_{shard}'
    directory.mkdir(parents=True,exist_ok=False)
    (ROOT/'logs').mkdir(exist_ok=True)
    order=order[shard::SHARDS]
    status=dict(status='running',expected=len(order),completed=0,rows=[],job=os.environ['SLURM_JOB_ID'])
    save(directory/'progress.json',status)
    try:
        for index,case in order:
            folder=ROOT/'tasks'/case['case_id']
            if not (folder/'summary.json').exists():
                assert not folder.exists(),'Partial case requires diagnosis'
                with (ROOT/'logs'/f"{case['case_id']}.log").open('x') as stream:
                    subprocess.run([str(ROOT.parent/'env_sim/bin/python'),str(ROOT/'physics_worker.py'),str(index)],
                        check=True,timeout=1800,stdout=stream,stderr=subprocess.STDOUT)
            checked=audit_case(read(folder/'result.json'))
            assert checked==read(folder/'summary.json')
            status['rows'].append(checked)
            status['completed']+=1
            save(directory/'progress.json',status)
        status['status']='completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        raise
    finally:
        save(directory/'progress.json',status)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['smoke','batch'])
    parser.add_argument('--shard',type=int,choices=range(SHARDS),required=True)
    args=parser.parse_args()
    run(args.phase,args.shard)
