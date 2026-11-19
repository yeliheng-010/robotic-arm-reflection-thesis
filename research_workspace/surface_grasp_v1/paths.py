import sys
from surface_grasp_v1.common import ROOT,read,save,verify
from surface_grasp_v1.planning import inspect


def select(catalogue, endpoints):
    safe={row['action_id'] for row in endpoints if row['ok']}
    rows=sorted((row for row in catalogue if row['id'] in safe),
                key=lambda row:-row['observed_distance_proxy_m'])
    chosen,remaining,seen=[],[],set()
    for row in rows:
        key=(row['anchor_id'],row['family'])
        if key in seen:
            remaining.append(row['id'])
        else:
            seen.add(key)
            chosen.append(row['id'])
    return (chosen+remaining)[:4]


def main(mode):
    assert mode in ('probe','audit')
    manifest=verify()
    assert read(ROOT/'audit/result.json')['passed']
    catalogue=read(ROOT/'catalogue.json')
    selected=select(catalogue,read(ROOT/'probe/endpoints.json'))
    by_id={row['id']:row for row in catalogue}
    rows=[]
    for name in selected:
        folder=ROOT/'paths'/mode/name
        result=inspect(by_id[name],manifest,folder)
        rows.append(dict(candidate=name,result=result))
        if mode=='audit':
            for file in ('private_plan.json','private_trace.json','private_events.json','state_check.json'):
                assert read(folder/file)==read(ROOT/'paths/probe'/name/file)
        if result['status']=='ready':
            break
    report=dict(selected_for_budget=selected,checked=rows,ready=any(r['result']['status']=='ready' for r in rows),
        independent=mode=='audit',physical_attempts=0,model_calls=0,full_task_success=None)
    save(ROOT/'paths'/mode/'result.json',report)
    print(dict(mode=mode,paths_checked=len(rows),ready=report['ready']),flush=True)


if __name__=='__main__':
    main(sys.argv[1])
