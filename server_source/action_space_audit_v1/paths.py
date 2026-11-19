import sys
from action_space_audit_v1.common import ROOT, read, save, verify
from action_space_audit_v1.catalogue import select
from model_grasp_gpu_v1.planning import inspect


def main(mode):
    assert mode in ('probe','audit')
    manifest = verify()
    assert read(ROOT/'audit/result.json')['passed']
    catalogue = read(ROOT/'catalogue.json')
    endpoints = read(ROOT/'probe/endpoints.json')
    selected = select(catalogue,endpoints,maximum=manifest['max_path_actions'])
    by_id = {r['id']:r for r in catalogue}
    rows = []
    for name in selected:
        folder = ROOT/'paths'/mode/name
        result = inspect(by_id[name]['proposal'],manifest,folder)
        rows.append(dict(action_id=name,result=result))
        if mode=='audit':
            for file in ('private_plan.json','private_trace.json','private_events.json','state_check.json'):
                assert read(folder/file)==read(ROOT/'paths/probe'/name/file)
        if result['status']=='ready':
            break
    result = dict(selected_for_budget=selected,checked=rows,
         ready=any(r['result']['status']=='ready' for r in rows),physical_attempts=0,model_calls=0,
         independent=mode=='audit',full_task_success=None,private_engineering_only=True)
    save(ROOT/'paths'/mode/'result.json',result)
    print(dict(mode=mode,path_actions_checked=len(rows),ready=result['ready']),flush=True)


if __name__=='__main__':
    main(sys.argv[1])
