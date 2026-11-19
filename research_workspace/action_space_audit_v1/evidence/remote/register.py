import numpy as np
from action_space_audit_v1.common import ROOT, PROJECT, SOURCE, QUALIFIED, MAX_ACTIONS
from action_space_audit_v1.common import ENDPOINT_SECONDS, PATH_SECONDS, read, save, sha
from action_space_audit_v1.catalogue import actions
from model_grasp_intent_v1.geometry import propose


def build_catalogue():
    nominal = np.asarray(read(QUALIFIED/'actual_plan.json')['context']['nominal'])[:3,3]
    with np.load(QUALIFIED/'span_inputs.npz') as arrays:
        points = arrays['world_points']
    return [dict(id=f'action_{i:03d}',action=action,proposal=propose(points,nominal,action))
            for i,action in enumerate(actions())]


def cached():
    rows = []
    audit = read(SOURCE/'audit/result.json')
    assert audit['passed'] and len(audit['plans'])==2
    original = read(QUALIFIED/'actual_plan.json')['context']
    for index in (1,2):
        folder = SOURCE/'run'/f'plan_{index}'
        plan = read(folder/'private_plan.json')
        assert plan['context']==original
        assert plan==read(SOURCE/'audit'/f'plan_{index}'/'private_plan.json')
        endpoints = [{k:v for k,v in r.items() if k not in ('id','pose')}
                     for r in plan['endpoints']['grasps']]
        assert len(endpoints)==8
        rows.append(dict(proposal=read(folder/'proposal.json'),endpoints=endpoints,
                         plan_sha256=sha(folder/'private_plan.json')))
    return rows


def main():
    source = read(SOURCE/'manifest.json')
    identities = dict(source['identities'])
    extras = list(ROOT.glob('*.py'))+list(ROOT.glob('*.sbatch'))+list(ROOT.glob('*.md'))
    extras += list(SOURCE.glob('run/plan_*/*.json'))+list(SOURCE.glob('audit/plan_*/*.json'))
    extras += [SOURCE/'audit/result.json',PROJECT/'model_grasp_gpu_v1/observation.json']
    for path in extras:
        identities[str(path)]=sha(path)
    for name,digest in identities.items():
        assert sha(name)==digest,name
    catalogue = build_catalogue()
    assert len(catalogue)==MAX_ACTIONS
    save(ROOT/'catalogue.json',catalogue)
    save(ROOT/'cached_endpoints.json',cached())
    for name in ('catalogue.json','cached_endpoints.json'):
        identities[str(ROOT/name)]=sha(ROOT/name)
    save(ROOT/'manifest.json',dict(case=source['case'],identities=identities,max_actions=MAX_ACTIONS,
         endpoint_seconds=ENDPOINT_SECONDS,planning_timeout_s=PATH_SECONDS,max_path_actions=4,
         physical_attempts=0,model_calls=0,training_runs=0,private_engineering_only=True))
    print(dict(registered=True,actions=len(catalogue),poses=sum(r['proposal']['status']=='proposal'
                                                            for r in catalogue)),flush=True)


if __name__=='__main__':
    main()
