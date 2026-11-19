import numpy as np
from surface_grasp_v1.common import ROOT,PROJECT,read,save,sha
from surface_grasp_v1.candidates import build

QUALIFIED=PROJECT/'qualification_strategy_v1/actual/cases/F1_964347_varied_noisy'


def generate():
    old=read(PROJECT/'action_space_audit_v1/catalogue.json')
    previous=[r['proposal']['pose'] for r in old if r['proposal']['status']=='proposal']
    observation=read(PROJECT/'model_grasp_gpu_v1/observation.json')
    camera=np.asarray(read(QUALIFIED/'span_guard.json')['transform'])[:3,3]
    return build(observation['target_points'],observation['scene_points'],
                 nominal=observation['nominal'],camera=camera,previous=previous)


def main():
    source=read(PROJECT/'action_space_audit_v1/manifest.json')
    identities=dict(source['identities'])
    for path in ROOT.iterdir():
        if path.suffix in ('.py','.sbatch','.md'):
            identities[str(path)]=sha(path)
    identities[str(PROJECT/'action_space_audit_v1/catalogue.json')]=sha(PROJECT/'action_space_audit_v1/catalogue.json')
    for name,digest in identities.items():
        assert sha(name)==digest,name
    result=generate()
    assert 0<len(result['catalogue'])<=512
    save(ROOT/'generation.json',result)
    save(ROOT/'catalogue.json',result['catalogue'])
    save(ROOT/'cached_endpoints.json',[])
    for name in ('generation.json','catalogue.json','cached_endpoints.json'):
        identities[str(ROOT/name)]=sha(ROOT/name)
    save(ROOT/'manifest.json',dict(case=source['case'],identities=identities,max_candidates=512,
         max_path_actions=4,endpoint_seconds=300,planning_timeout_s=120,model_calls=0,
         physical_attempts=0,training_runs=0,private_engineering_only=True))
    print(result['summary'],flush=True)


if __name__=='__main__':
    main()
