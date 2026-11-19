import sys
import json
from reflection.__main__ import bootstrap
bootstrap()
from ot_inputs import opened
from hp_search import choose
from register import RUN,save,sha,verify
from cc_common import read


def main(name, mode):
    entry=next(r for r in verify(RUN/'manifest.json')['rows'] if r['name']==name)
    folder=RUN/mode/name
    folder.mkdir(parents=True,exist_ok=False)
    with open(entry['endpoint_path']) as stream:
        goals=[r for r in map(json.loads,stream) if r['ok']]
    with (folder/'checks.jsonl').open('x') as stream:
        def record(stage, row):
            stream.write(json.dumps(dict(stage=stage,result=row),allow_nan=False)+'\n')
            stream.flush()
        with opened(entry) as (flow,grasps,poses):
            plan=choose(flow,item=entry['case']['item'],parameters=entry['case']['state']['parameters'],
                goals=goals,record=record)
    save(folder/'plan.json',plan)
    if mode=='audit':
        assert plan==read(RUN/'probe'/name/'plan.json')
        assert sha(folder/'checks.jsonl')==sha(RUN/'probe'/name/'checks.jsonl')
    save(folder/'result.json',dict(passed=True,qualified=plan['selected'] is not None,
        status=plan['status'],prefix_checks=len(plan['prefixes']),carry_checks=len(plan['carry']),
        joint_checks=len(plan['events']),independent=mode=='audit',physical_attempts=0,model_calls=0,
        identities={str(p):sha(p) for p in folder.glob('*')}))
    print(dict(name=name,mode=mode,qualified=plan['selected'] is not None,status=plan['status'],
        prefixes=len(plan['prefixes']),carry=len(plan['carry']),joint_checks=len(plan['events'])),flush=True)


if __name__=='__main__':
    main(*sys.argv[1:])
