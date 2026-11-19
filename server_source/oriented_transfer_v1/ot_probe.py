import sys
import json
from pathlib import Path
from collections import Counter
from reflection.__main__ import bootstrap
bootstrap()
from routecheck.static import state,unchanged
from ot_inputs import opened
from ot_endpoints import inspect
from ot_register import ROOT,RUN,save,sha,verify
from cc_common import read


def main(name, mode):
    entry=next(r for r in verify(RUN/'manifest.json')['rows'] if r['name']==name)
    folder=RUN/mode/name
    folder.mkdir(parents=True,exist_ok=False)
    with (folder/'endpoints.jsonl').open('x') as stream:
        def record(row):
            stream.write(json.dumps(row,allow_nan=False)+'\n')
            stream.flush()
        with opened(entry) as (flow,grasps,poses):
            before=state(flow.robot,flow.env)
            rows,status=inspect(flow,item=entry['case']['item'],grasps=grasps,poses=poses,record=record)
            unchanged(before,state(flow.robot,flow.env))
    ledger=folder/'endpoints.jsonl'
    if mode=='audit':
        assert sha(ledger)==sha(RUN/'probe'/name/'endpoints.jsonl')
    summary=dict(passed=True,endpoint_qualified=any(r['ok'] for r in rows),full_plan_qualified=False,
        safe_grasps=len(grasps),endpoint_checks=len(rows),safe_endpoints=sum(r['ok'] for r in rows),
        reasons=dict(Counter(r.get('reason') or 'ok' for r in rows)),status=status,
        independent=mode=='audit',physical_attempts=0,model_calls=0,unchanged=True)
    save(folder/'result.json',dict(summary,identities={str(ledger):sha(ledger)}))
    print(dict(name=name,mode=mode,**summary),flush=True)


if __name__=='__main__':
    main(*sys.argv[1:])
